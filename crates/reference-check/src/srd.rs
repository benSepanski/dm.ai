//! Loading + indexing the extracted SRD 5.2.1 Markdown mirror. Parsing is
//! deliberately narrow: the handful of tables and bullet lines the 5.5e
//! comparator (`dnd5e.rs`) reads, keyed by normalized record name. Nothing
//! parsed here is ever written anywhere — diagnostics name fields, never
//! source values.
//!
//! Mirror shape (dnd/521/markdown/): one page per species, feat, tool, and
//! gear item (`# Title` then `- **Key:** value` bullets or a small table);
//! `Equipment/Weapons.md` and `Equipment/Armor.md` hold the printed tables;
//! `Backgrounds/Character Origins.md` holds the four backgrounds as `####`
//! sections; `Classes/<Class>/<Class>.md` holds the core-traits table, the
//! features table, and `## <Class> Subclass: <Name>` sections; skills are a
//! table in `Playing/Proficiency.md`; the ability-score methods are
//! paragraphs plus a cost table in `Character Creation/Step 3 Ability
//! Scores.md`. The mirror is a PDF split, so a few table cells carry
//! line-break spacing artifacts inside words; comparators that read those
//! cells strip whitespace before comparing (documented at each site).

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::foundry::normalize_name;
use crate::{cache, System};

/// Paths under `dnd/521/markdown/` the matcher reads. Only these are
/// extracted — the tarball also carries the whole 5.1 SRD, monsters,
/// spells, and the PDFs the tool has no use for on disk.
pub const NEEDED_PATHS: &[&str] = &[
    "Species/",
    "Backgrounds/",
    "Feats/",
    "Classes/Fighter/",
    "Equipment/",
    "Playing/Proficiency.md",
    "Character Creation/Step 3 Ability Scores.md",
];

fn markdown_root() -> PathBuf {
    cache::source_root(System::Dnd5e)
        .join("dnd")
        .join("521")
        .join("markdown")
}

// ---- generic markdown helpers ---------------------------------------------

pub struct Table {
    pub header: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl Table {
    pub fn column(&self, name: &str) -> Option<usize> {
        self.header
            .iter()
            .position(|h| h.trim().eq_ignore_ascii_case(name))
    }
}

fn split_cells(line: &str) -> Vec<String> {
    let inner = line.trim().trim_start_matches('|').trim_end_matches('|');
    inner.split('|').map(|c| c.trim().to_string()).collect()
}

fn is_separator(cells: &[String]) -> bool {
    !cells.is_empty()
        && cells
            .iter()
            .all(|c| !c.is_empty() && c.chars().all(|ch| ch == '-' || ch == ':'))
}

/// Every pipe table in the text, in order.
pub fn tables(text: &str) -> Vec<Table> {
    let mut out = Vec::new();
    let mut current: Option<Table> = None;
    for line in text.lines() {
        if line.trim_start().starts_with('|') {
            let cells = split_cells(line);
            match current.as_mut() {
                None => {
                    current = Some(Table {
                        header: cells,
                        rows: Vec::new(),
                    });
                }
                Some(t) => {
                    if !is_separator(&cells) {
                        t.rows.push(cells);
                    }
                }
            }
        } else if let Some(t) = current.take() {
            out.push(t);
        }
    }
    if let Some(t) = current.take() {
        out.push(t);
    }
    out
}

/// `- **Key:** value` (or `**Key:** value`) → value.
pub fn bullet(text: &str, key: &str) -> Option<String> {
    let marker = format!("**{key}:**");
    text.lines().find_map(|l| {
        let l = l.trim().trim_start_matches("- ").trim();
        l.strip_prefix(&marker).map(|v| v.trim().to_string())
    })
}

/// `# Title` (the first level-1 heading).
pub fn title(text: &str) -> Option<String> {
    text.lines()
        .find_map(|l| l.strip_prefix("# ").map(|t| t.trim().to_string()))
}

/// `_**Name.**_ text` trait headings, in order.
pub fn trait_headings(text: &str) -> Vec<String> {
    text.lines()
        .filter_map(|l| {
            l.trim()
                .strip_prefix("_**")
                .and_then(|r| r.split_once(".**_"))
                .map(|(name, _)| name.trim().to_string())
        })
        .collect()
}

/// `**Name.** text` bold-run headings (a trait's choice options).
pub fn bold_headings(text: &str) -> Vec<String> {
    text.lines()
        .filter_map(|l| {
            l.trim()
                .strip_prefix("**")
                .and_then(|r| r.split_once(".**"))
                .map(|(name, _)| name.trim().to_string())
        })
        .collect()
}

/// (heading, body) for every heading of exactly `level`; the body runs to
/// the next heading of `level` or shallower.
pub fn sections(text: &str, level: usize) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut open = false;
    for line in text.lines() {
        let hashes = line.chars().take_while(|c| *c == '#').count();
        if hashes > 0 && line[hashes..].starts_with(' ') {
            if hashes == level {
                out.push((line[hashes..].trim().to_string(), String::new()));
                open = true;
                continue;
            }
            if hashes < level {
                open = false;
            }
        }
        if open {
            if let Some((_, body)) = out.last_mut() {
                body.push_str(line);
                body.push('\n');
            }
        }
    }
    out
}

/// Split on `sep` outside parentheses.
pub fn split_top(text: &str, sep: char) -> Vec<String> {
    let mut out = Vec::new();
    let mut depth = 0i32;
    let mut cur = String::new();
    for c in text.chars() {
        match c {
            '(' => {
                depth += 1;
                cur.push(c);
            }
            ')' => {
                depth -= 1;
                cur.push(c);
            }
            c if c == sep && depth == 0 => {
                out.push(cur.trim().to_string());
                cur.clear();
            }
            c => cur.push(c),
        }
    }
    if !cur.trim().is_empty() {
        out.push(cur.trim().to_string());
    }
    out
}

/// "Name (qualifier)" → ("Name", Some("qualifier")).
pub fn split_paren(text: &str) -> (String, Option<String>) {
    match text.split_once(" (") {
        Some((name, rest)) => (
            name.trim().to_string(),
            Some(rest.trim_end_matches(')').trim().to_string()),
        ),
        None => (text.trim().to_string(), None),
    }
}

/// "1 SP" / "25 GP" / "5 CP" / "1,500 GP" → copper pieces; "—", "Varies",
/// or anything else → None.
pub fn cost_cp(text: &str) -> Option<i64> {
    let mut parts = text.split_whitespace();
    let amount: i64 = parts.next()?.replace(',', "").parse().ok()?;
    let unit = parts.next()?.to_ascii_uppercase();
    let mult = match unit.as_str() {
        "CP" => 1,
        "SP" => 10,
        "EP" => 50,
        "GP" => 100,
        "PP" => 1000,
        _ => return None,
    };
    Some(amount * mult)
}

/// "2 lb." / "1/4 lb." / "1 1/2 lb." / "5 lb. (full)" → pounds; "—" → 0;
/// "Varies" or anything else → None.
pub fn weight_lb(text: &str) -> Option<f64> {
    let text = text.trim();
    if text == "—" {
        return Some(0.0);
    }
    let mut total = 0.0;
    let mut seen = false;
    for tok in text.split_whitespace() {
        if tok.starts_with("lb") {
            break;
        }
        if let Some((n, d)) = tok.split_once('/') {
            let n: f64 = n.parse().ok()?;
            let d: f64 = d.parse().ok()?;
            total += n / d;
        } else {
            total += tok.parse::<f64>().ok()?;
        }
        seen = true;
    }
    seen.then_some(total)
}

/// "Strength" → "str" (the shipped abbreviation vocabulary).
pub fn ability_abbr(name: &str) -> String {
    let lower = name.trim().to_lowercase();
    match lower.as_str() {
        "strength" => "str",
        "dexterity" => "dex",
        "constitution" => "con",
        "intelligence" => "int",
        "wisdom" => "wis",
        "charisma" => "cha",
        _ => "",
    }
    .to_string()
}

fn first_int(text: &str) -> Option<i64> {
    text.split(|c: char| !c.is_ascii_digit())
        .find(|s| !s.is_empty())
        .and_then(|s| s.parse().ok())
}

// ---- indexed source -------------------------------------------------------

pub struct WeaponRow {
    /// The printed name (the reverse sweep reports it).
    pub name: String,
    pub category: String, // simple | martial
    pub kind: String,     // melee | ranged
    pub damage: String,   // "1d4" / "1"
    pub damage_type: String,
    pub properties: Vec<String>,
    pub versatile: Option<String>,
    pub range: Option<String>,
    pub ammunition: Option<String>,
    pub mastery: String,
    pub weight: Option<f64>,
    pub cost: Option<i64>,
}

pub struct ArmorRow {
    /// The printed name (the reverse sweep reports it).
    pub name: String,
    pub category: String, // light | medium | heavy | shield
    pub base_ac: i64,
    pub add_dex: bool,
    pub dex_max: Option<i64>,
    /// None when the table has no Strength column (the Shield table).
    pub strength: Option<Option<i64>>,
    /// None when the table has no Stealth column (the Shield table).
    pub stealth: Option<bool>,
    pub weight: Option<f64>,
    pub cost: Option<i64>,
}

pub struct GearRow {
    pub weight: Option<f64>,
    pub cost: Option<i64>,
    /// The Amount column of a per-lot table (ammunition).
    pub amount: Option<i64>,
}

pub struct SpeciesPage {
    pub name: String,
    pub creature_type: String,
    pub sizes: Vec<String>,
    pub speed: Option<i64>,
    pub darkvision: Option<i64>,
    pub traits: Vec<String>,
    pub options: Vec<String>,
}

pub struct BackgroundEntry {
    pub name: String,
    pub abilities: Vec<String>,
    pub feat: String,
    pub skills: Vec<String>,
    pub tool: String,
    pub package_items: usize,
    pub package_gold: Option<i64>,
    pub gold_alternative: Option<i64>,
}

pub struct FeatPage {
    pub name: String,
    /// "origin" | "fighting-style" | "general" | "epic-boon"
    pub category: String,
}

pub struct ClassPage {
    pub name: String,
    /// Core traits table: row label → value.
    pub core: BTreeMap<String, String>,
    /// The class-features table (Level | Proficiency Bonus | Class
    /// Features | ...), for column lookups by header.
    pub features: Option<Table>,
}

pub struct SubclassSection {
    pub class: String,
    pub features: Vec<(i64, String)>,
}

pub struct ScoreMethod {
    pub name: String,
    pub array: Vec<i64>,
    pub budget: Option<i64>,
    pub costs: BTreeMap<String, i64>,
}

pub struct ToolPage {
    pub weight: Option<f64>,
    pub cost: Option<i64>,
    /// Prices of the listed variants when the cost "Varies".
    pub variant_costs: Vec<i64>,
}

pub struct Srd {
    pub weapons: BTreeMap<String, WeaponRow>,
    pub armor: BTreeMap<String, ArmorRow>,
    /// Adventuring Gear table rows, keyed by normalized name and by the
    /// comma-inverted form ("Clothes, Traveler's" → "traveler's clothes").
    pub gear: BTreeMap<String, GearRow>,
    /// Per-item variant tables (Ammunition types, Holy Symbol forms) for
    /// gear-table rows whose weight/cost "Varies": base name → variant
    /// name → row.
    pub variants: BTreeMap<String, BTreeMap<String, GearRow>>,
    pub species: BTreeMap<String, SpeciesPage>,
    pub backgrounds: BTreeMap<String, BackgroundEntry>,
    pub feats: BTreeMap<String, FeatPage>,
    pub skills: BTreeMap<String, String>,
    pub classes: BTreeMap<String, ClassPage>,
    pub subclasses: BTreeMap<String, SubclassSection>,
    pub score_array: Option<ScoreMethod>,
    pub score_points: Option<ScoreMethod>,
    /// Equipment pages by normalized title (tool lookups).
    equipment_pages: BTreeMap<String, PathBuf>,
}

fn read(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| format!("reading {}: {e}", path.display()))
}

fn list_dir(dir: &Path) -> Result<Vec<PathBuf>, String> {
    let mut out: Vec<PathBuf> = fs::read_dir(dir)
        .map_err(|e| format!("reading {}: {e}", dir.display()))?
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "md"))
        .collect();
    out.sort();
    Ok(out)
}

/// "Clothes, Traveler's" → "Traveler's Clothes".
fn invert_comma(name: &str) -> Option<String> {
    let (head, tail) = name.split_once(", ")?;
    Some(format!("{} {}", tail.trim(), head.trim()))
}

pub fn load() -> Result<Srd, String> {
    let root = markdown_root();
    let equipment = root.join("Equipment");

    let mut equipment_pages = BTreeMap::new();
    for path in list_dir(&equipment)? {
        let text = read(&path)?;
        if let Some(t) = title(&text) {
            equipment_pages.insert(normalize_name(&t), path);
        }
    }

    let mut srd = Srd {
        weapons: BTreeMap::new(),
        armor: BTreeMap::new(),
        gear: BTreeMap::new(),
        variants: BTreeMap::new(),
        species: BTreeMap::new(),
        backgrounds: BTreeMap::new(),
        feats: BTreeMap::new(),
        skills: BTreeMap::new(),
        classes: BTreeMap::new(),
        subclasses: BTreeMap::new(),
        score_array: None,
        score_points: None,
        equipment_pages,
    };

    load_weapons(&mut srd, &read(&equipment.join("Weapons.md"))?)?;
    load_armor(&mut srd, &read(&equipment.join("Armor.md"))?)?;
    load_gear(&mut srd, &read(&equipment.join("Adventuring Gear.md"))?)?;
    for path in list_dir(&root.join("Species"))? {
        load_species(&mut srd, &read(&path)?);
    }
    load_backgrounds(
        &mut srd,
        &read(&root.join("Backgrounds").join("Character Origins.md"))?,
    );
    for path in list_dir(&root.join("Feats"))? {
        load_feat(&mut srd, &read(&path)?);
    }
    for class_dir in fs::read_dir(root.join("Classes"))
        .map_err(|e| format!("reading Classes: {e}"))?
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.is_dir())
    {
        for path in list_dir(&class_dir)? {
            load_class(&mut srd, &read(&path)?);
        }
    }
    load_skills(
        &mut srd,
        &read(&root.join("Playing").join("Proficiency.md"))?,
    )?;
    load_scores(
        &mut srd,
        &read(
            &root
                .join("Character Creation")
                .join("Step 3 Ability Scores.md"),
        )?,
    );
    Ok(srd)
}

fn load_weapons(srd: &mut Srd, text: &str) -> Result<(), String> {
    for table in tables(text) {
        let Some(head) = table.header.first() else {
            continue;
        };
        let head_l = head.to_lowercase();
        if !head_l.ends_with("weapons") {
            continue;
        }
        let category = if head_l.starts_with("simple") {
            "simple"
        } else {
            "martial"
        };
        let kind = if head_l.contains("melee") {
            "melee"
        } else {
            "ranged"
        };
        let (Some(dmg), Some(props), Some(mastery), Some(weight), Some(cost)) = (
            table.column("Damage"),
            table.column("Properties"),
            table.column("Mastery"),
            table.column("Weight"),
            table.column("Cost"),
        ) else {
            return Err("Weapons.md: a weapon table lacks an expected column".to_string());
        };
        for row in &table.rows {
            let (damage, damage_type) = row[dmg]
                .split_once(' ')
                .map(|(d, t)| (d.to_string(), t.to_string()))
                .unwrap_or((row[dmg].clone(), String::new()));
            let mut properties = Vec::new();
            let mut versatile = None;
            let mut range = None;
            let mut ammunition = None;
            if row[props] != "—" {
                for prop in split_top(&row[props], ',') {
                    let (name, paren) = split_paren(&prop);
                    match (name.as_str(), paren) {
                        ("Versatile", Some(p)) => {
                            versatile = Some(p);
                            properties.push(name);
                        }
                        (_, Some(p)) if p.starts_with("Range ") => {
                            let spec = p.trim_start_matches("Range ");
                            match spec.split_once(';') {
                                Some((r, ammo)) => {
                                    range = Some(r.trim().to_string());
                                    ammunition = Some(ammo.trim().to_string());
                                }
                                None => range = Some(spec.trim().to_string()),
                            }
                            properties.push(name);
                        }
                        // Any other qualifier is part of the property as
                        // printed ("Two-Handed (unless mounted)").
                        (_, Some(_)) => properties.push(prop.clone()),
                        (_, None) => properties.push(name),
                    }
                }
            }
            srd.weapons.insert(
                normalize_name(&row[0]),
                WeaponRow {
                    name: row[0].clone(),
                    category: category.to_string(),
                    kind: kind.to_string(),
                    damage,
                    damage_type,
                    properties,
                    versatile,
                    range,
                    ammunition,
                    mastery: row[mastery].clone(),
                    weight: weight_lb(&row[weight]),
                    cost: cost_cp(&row[cost]),
                },
            );
        }
    }
    if srd.weapons.is_empty() {
        return Err("Weapons.md: no weapon tables parsed".to_string());
    }
    Ok(())
}

fn load_armor(srd: &mut Srd, text: &str) -> Result<(), String> {
    for table in tables(text) {
        let Some(head) = table.header.first() else {
            continue;
        };
        let head_l = head.to_lowercase();
        let category = if head_l.starts_with("light") {
            "light"
        } else if head_l.starts_with("medium") {
            "medium"
        } else if head_l.starts_with("heavy") {
            "heavy"
        } else if head_l.starts_with("shield") {
            "shield"
        } else {
            continue;
        };
        let (Some(ac), Some(weight), Some(cost)) = (
            table
                .header
                .iter()
                .position(|h| h.to_lowercase().starts_with("armor class")),
            table.column("Weight"),
            table.column("Cost"),
        ) else {
            return Err("Armor.md: an armor table lacks an expected column".to_string());
        };
        let strength_col = table.column("Strength");
        let stealth_col = table.column("Stealth");
        for row in &table.rows {
            let ac_cell = row[ac].trim();
            let base_ac = first_int(ac_cell).unwrap_or(-1);
            let add_dex = ac_cell.to_lowercase().contains("dex");
            let dex_max = ac_cell.split_once("(max ").and_then(|(_, m)| first_int(m));
            let strength = strength_col.map(|c| {
                let cell = row[c].trim();
                if cell == "—" {
                    None
                } else {
                    first_int(cell)
                }
            });
            let stealth = stealth_col.map(|c| row[c].trim().eq_ignore_ascii_case("disadvantage"));
            srd.armor.insert(
                normalize_name(&row[0]),
                ArmorRow {
                    name: row[0].clone(),
                    category: category.to_string(),
                    base_ac,
                    add_dex,
                    dex_max,
                    strength,
                    stealth,
                    weight: weight_lb(&row[weight]),
                    cost: cost_cp(&row[cost]),
                },
            );
        }
    }
    if srd.armor.is_empty() {
        return Err("Armor.md: no armor tables parsed".to_string());
    }
    Ok(())
}

fn gear_row(table: &Table, row: &[String]) -> GearRow {
    GearRow {
        weight: table.column("Weight").and_then(|c| weight_lb(&row[c])),
        cost: table.column("Cost").and_then(|c| cost_cp(&row[c])),
        amount: table.column("Amount").and_then(|c| first_int(&row[c])),
    }
}

fn load_gear(srd: &mut Srd, text: &str) -> Result<(), String> {
    let Some(table) = tables(text)
        .into_iter()
        .find(|t| t.column("Item").is_some())
    else {
        return Err("Adventuring Gear.md: no item table".to_string());
    };
    let mut varies: Vec<String> = Vec::new();
    for row in &table.rows {
        let name = &row[0];
        let entry = gear_row(&table, row);
        if entry.weight.is_none() && entry.cost.is_none() {
            varies.push(name.clone());
        }
        if let Some(inv) = invert_comma(name) {
            srd.gear.insert(normalize_name(&inv), gear_row(&table, row));
        }
        srd.gear.insert(normalize_name(name), entry);
    }
    // Per-item variant tables for "Varies" rows that have their own page.
    for name in varies {
        let Some(path) = srd.equipment_pages.get(&normalize_name(&name)) else {
            continue;
        };
        let page = read(path)?;
        let mut rows = BTreeMap::new();
        for table in tables(&page) {
            if table.column("Cost").is_none() {
                continue;
            }
            for row in &table.rows {
                let (variant, _) = split_paren(&row[0]);
                rows.insert(normalize_name(&variant), gear_row(&table, row));
            }
        }
        if !rows.is_empty() {
            srd.variants.insert(normalize_name(&name), rows);
        }
    }
    Ok(())
}

fn load_species(srd: &mut Srd, text: &str) {
    let (Some(name), Some(creature_type), Some(size_line)) = (
        title(text),
        bullet(text, "Creature Type"),
        bullet(text, "Size"),
    ) else {
        return; // the "Character Species" overview page
    };
    let sizes: Vec<String> = size_line
        .split(|c: char| !c.is_alphabetic())
        .filter(|w| matches!(*w, "Tiny" | "Small" | "Medium" | "Large"))
        .map(str::to_string)
        .collect();
    let speed = bullet(text, "Speed").and_then(|s| first_int(&s));
    let darkvision = text
        .lines()
        .find(|l| l.trim().starts_with("_**Darkvision.**_"))
        .and_then(first_int);
    srd.species.insert(
        normalize_name(&name),
        SpeciesPage {
            name,
            creature_type,
            sizes,
            speed,
            darkvision,
            traits: trait_headings(text),
            options: bold_headings(text),
        },
    );
}

fn strip_see_also(text: &str) -> String {
    let t = match text.find(" (see ") {
        Some(i) => &text[..i],
        None => text,
    };
    t.replace('_', "").trim().to_string()
}

fn load_backgrounds(srd: &mut Srd, text: &str) {
    let Some((_, descriptions)) = sections(text, 3)
        .into_iter()
        .find(|(h, _)| h.eq_ignore_ascii_case("Background Descriptions"))
    else {
        return;
    };
    for (name, body) in sections(&descriptions, 4) {
        let abilities = bullet(&body, "Ability Scores")
            .map(|s| s.split(',').map(ability_abbr).collect())
            .unwrap_or_default();
        let feat = bullet(&body, "Feat")
            .map(|s| strip_see_also(&s))
            .unwrap_or_default();
        let skills = bullet(&body, "Skill Proficiencies")
            .map(|s| s.split(" and ").map(|x| x.trim().to_string()).collect())
            .unwrap_or_default();
        let tool = bullet(&body, "Tool Proficiency")
            .map(|s| strip_see_also(&s))
            .unwrap_or_default();
        let (package_items, package_gold, gold_alternative) = bullet(&body, "Equipment")
            .map(|s| parse_choice_packages(&s))
            .map(|packages| {
                let a = packages.iter().find(|p| p.label == "A");
                let b = packages.iter().find(|p| p.label == "B");
                (
                    a.map(|p| p.items).unwrap_or(0),
                    a.and_then(|p| p.gold),
                    b.and_then(|p| p.gold),
                )
            })
            .unwrap_or((0, None, None));
        srd.backgrounds.insert(
            normalize_name(&name),
            BackgroundEntry {
                name,
                abilities,
                feat,
                skills,
                tool,
                package_items,
                package_gold,
                gold_alternative,
            },
        );
    }
}

/// A labeled starting-equipment package: item-line count and coin.
pub struct Package {
    pub label: String,
    pub items: usize,
    pub gold: Option<i64>,
}

/// "_Choose A or B:_ (A) X, Y, 8 GP; or (B) 50 GP" / "Choose A, B, or C:
/// (A) …, and 4 GP; (B) …, and 11 GP; or (C) 155 GP" → packages.
pub fn parse_choice_packages(text: &str) -> Vec<Package> {
    let body = match text.find("(A)") {
        Some(i) => &text[i..],
        None => text,
    };
    let mut out = Vec::new();
    for part in body.split(';') {
        let part = part.trim().trim_start_matches("or ").trim();
        let Some(rest) = part.strip_prefix('(') else {
            continue;
        };
        let Some((label, items)) = rest.split_once(") ") else {
            continue;
        };
        let entries = split_top(items, ',');
        let last = entries
            .last()
            .map(|s| s.trim_start_matches("and ").trim().to_string())
            .unwrap_or_default();
        let gold = cost_cp(&last).map(|cp| cp / 100);
        let items = if gold.is_some() {
            entries.len() - 1
        } else {
            entries.len()
        };
        out.push(Package {
            label: label.to_string(),
            items,
            gold,
        });
    }
    out
}

fn load_feat(srd: &mut Srd, text: &str) {
    let Some(name) = title(text) else {
        return;
    };
    let Some(line) = text
        .lines()
        .map(str::trim)
        .find(|l| l.starts_with('_') && !l.starts_with("_**") && l.contains(" Feat"))
    else {
        return; // the "Feats" overview page
    };
    let category = line
        .trim_matches('_')
        .split(" Feat")
        .next()
        .unwrap_or("")
        .trim()
        .to_lowercase()
        .replace(' ', "-");
    srd.feats
        .insert(normalize_name(&name), FeatPage { name, category });
}

fn load_class(srd: &mut Srd, text: &str) {
    let Some(name) = title(text) else {
        return;
    };
    let all = tables(text);
    let mut core = BTreeMap::new();
    let mut features = None;
    for table in all {
        if table.header.first().is_some_and(|h| h == "Level") {
            features = Some(table);
        } else if table.header.len() == 2 {
            // The two-column traits table: the mirror renders its first
            // row as the header.
            core.insert(table.header[0].clone(), table.header[1].clone());
            for row in &table.rows {
                if row.len() == 2 {
                    core.insert(row[0].clone(), row[1].clone());
                }
            }
        }
    }
    if features.is_none() && core.is_empty() {
        return; // a spell list page
    }
    for (heading, body) in sections(text, 2) {
        let Some((class, sub)) = heading.split_once(" Subclass: ") else {
            continue;
        };
        let feats: Vec<(i64, String)> = sections(&body, 3)
            .into_iter()
            .filter_map(|(h, _)| {
                let (level, fname) = h.strip_prefix("Level ")?.split_once(": ")?;
                Some((level.parse().ok()?, fname.trim().to_string()))
            })
            .collect();
        srd.subclasses.insert(
            normalize_name(sub),
            SubclassSection {
                class: class.trim().to_string(),
                features: feats,
            },
        );
    }
    srd.classes.insert(
        normalize_name(&name),
        ClassPage {
            name,
            core,
            features,
        },
    );
}

fn load_skills(srd: &mut Srd, text: &str) -> Result<(), String> {
    let Some(table) = tables(text)
        .into_iter()
        .find(|t| t.column("Skill").is_some() && t.column("Ability").is_some())
    else {
        return Err("Proficiency.md: no skill table".to_string());
    };
    let ability = table.column("Ability").expect("checked");
    for row in &table.rows {
        srd.skills
            .insert(normalize_name(&row[0]), ability_abbr(&row[ability]));
    }
    Ok(())
}

fn load_scores(srd: &mut Srd, text: &str) {
    let costs: BTreeMap<String, i64> = tables(text)
        .into_iter()
        .find(|t| t.column("Score").is_some() && t.column("Cost").is_some())
        .map(|t| {
            let cost = t.column("Cost").expect("checked");
            t.rows
                .iter()
                .filter_map(|r| Some((r[0].trim().to_string(), r[cost].trim().parse().ok()?)))
                .collect()
        })
        .unwrap_or_default();
    for line in text.lines() {
        let Some(rest) = line.trim().strip_prefix("_**") else {
            continue;
        };
        let Some((name, body)) = rest.split_once(".**_") else {
            continue;
        };
        let body_l = body.to_lowercase();
        if body_l.contains("six scores") {
            let array = body
                .rsplit(':')
                .next()
                .unwrap_or("")
                .split(',')
                .filter_map(|n| n.trim().trim_end_matches('.').parse().ok())
                .collect();
            srd.score_array = Some(ScoreMethod {
                name: name.to_string(),
                array,
                budget: None,
                costs: BTreeMap::new(),
            });
        } else if body_l.contains("points to spend") {
            srd.score_points = Some(ScoreMethod {
                name: name.to_string(),
                array: Vec::new(),
                budget: first_int(body),
                costs: costs.clone(),
            });
        }
    }
}

impl Srd {
    /// A tool's own page: cost, weight, and variant prices.
    pub fn tool(&self, normalized_name: &str) -> Result<Option<ToolPage>, String> {
        let Some(path) = self.equipment_pages.get(normalized_name) else {
            return Ok(None);
        };
        let text = read(path)?;
        let (Some(cost), Some(weight)) = (bullet(&text, "Cost"), bullet(&text, "Weight")) else {
            return Ok(None); // not a tool page
        };
        let variant_costs = bullet(&text, "Variants")
            .map(|v| {
                split_top(&v, ',')
                    .iter()
                    .filter_map(|entry| split_paren(entry).1)
                    .filter_map(|p| cost_cp(&p))
                    .collect()
            })
            .unwrap_or_default();
        Ok(Some(ToolPage {
            weight: weight_lb(&weight),
            cost: cost_cp(&cost),
            variant_costs,
        }))
    }
}
