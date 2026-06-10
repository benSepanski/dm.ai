import type { CharacterResponse, CombatStateResponse } from "./client";
import type { ActiveCombat, CharacterData } from "../store/gameStore";

// Maps API response shapes to store shapes. Shared by the WebSocket event
// handlers and the session-resume hydration so the two paths can't drift.

export function mapCharacterResponse(char: CharacterResponse): CharacterData {
  return {
    id: char.id,
    type: char.type,
    name: char.name,
    char_class: char.char_class,
    race: char.race,
    level: char.level,
    hp_current: char.hp_current,
    hp_max: char.hp_max,
    ac: char.ac,
    stats: char.stats,
  };
}

export function mapCombatResponse(combat: CombatStateResponse): ActiveCombat {
  const order = combat.initiative_order ?? [];
  const data = combat.combatants ?? [];
  return {
    id: combat.id,
    round_number: combat.round_number,
    current_turn_index: combat.current_turn_index,
    combatants: order.map((entry, i) => ({
      char_id: entry.character_id,
      name: entry.name,
      hp_current: data[i]?.hp_current ?? 0,
      hp_max: data[i]?.hp_max ?? 0,
      ac: data[i]?.ac ?? 10,
      initiative: entry.initiative,
      is_current_turn: i === combat.current_turn_index,
    })),
  };
}
