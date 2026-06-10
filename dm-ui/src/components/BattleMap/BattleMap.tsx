import { Stage, Layer, Rect, Circle, Text, Line } from "react-konva";
import type Konva from "konva";
import { useGameStore, type TokenPosition } from "../../store/gameStore";

const CELL = 50;
const COLS = 10;
const ROWS = 10;
const W = CELL * COLS;
const H = CELL * ROWS;

const PARTY_COLOR = "#3498db";
const ENEMY_COLOR = "#c0392b";
const DOWNED_COLOR = "#555";

interface Token {
  id: string;
  name: string;
  color: string;
  gridX: number;
  gridY: number;
}

interface BattleMapProps {
  // Called when the local user drags a token; the dashboard persists the move
  // and relays it to the other connected clients over the WebSocket.
  onTokenMove: (tokenId: string, x: number, y: number) => void;
}

function GridLines() {
  const lines = [];
  for (let i = 0; i <= COLS; i++) {
    lines.push(
      <Line
        key={`v${i}`}
        points={[i * CELL, 0, i * CELL, H]}
        stroke="#333"
        strokeWidth={1}
      />
    );
  }
  for (let j = 0; j <= ROWS; j++) {
    lines.push(
      <Line
        key={`h${j}`}
        points={[0, j * CELL, W, j * CELL]}
        stroke="#333"
        strokeWidth={1}
      />
    );
  }
  return <>{lines}</>;
}

function TokenShape({
  token,
  onMove,
}: {
  token: Token;
  onMove: (id: string, gx: number, gy: number) => void;
}) {
  const handleDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    const gx = Math.max(0, Math.min(COLS - 1, Math.round(e.target.x() / CELL)));
    const gy = Math.max(0, Math.min(ROWS - 1, Math.round(e.target.y() / CELL)));
    e.target.setAttrs({ x: gx * CELL + CELL / 2, y: gy * CELL + CELL / 2 });
    onMove(token.id, gx, gy);
  };

  return (
    <>
      <Circle
        x={token.gridX * CELL + CELL / 2}
        y={token.gridY * CELL + CELL / 2}
        radius={CELL * 0.38}
        fill={token.color}
        draggable
        onDragEnd={handleDragEnd}
        shadowBlur={4}
        shadowColor="black"
      />
      <Text
        x={token.gridX * CELL}
        y={token.gridY * CELL + CELL * 0.65}
        width={CELL}
        text={token.name.slice(0, 4)}
        fontSize={9}
        fill="#fff"
        align="center"
        listening={false}
      />
    </>
  );
}

// Party tokens line up near the top edge, enemies near the bottom, until
// someone drags them somewhere better.
function defaultPosition(isParty: boolean, sideIndex: number): TokenPosition {
  return {
    x: (1 + sideIndex) % COLS,
    y: isParty ? 1 : ROWS - 2,
  };
}

export default function BattleMap({ onTokenMove }: BattleMapProps) {
  const combat = useGameStore((s) => s.combat);
  const characters = useGameStore((s) => s.characters);
  const tokenPositions = useGameStore((s) => s.tokenPositions);

  // During combat, tokens mirror the combatants in initiative order; outside
  // combat, show the party roster so the DM can stage a scene.
  const partyIds = new Set(characters.map((c) => c.id));
  const sources = combat
    ? combat.combatants.map((c) => ({
        id: c.char_id,
        name: c.name,
        isParty: partyIds.has(c.char_id),
        isDowned: c.hp_current <= 0,
      }))
    : characters.map((c) => ({
        id: c.id,
        name: c.name,
        isParty: true,
        isDowned: (c.hp_current ?? 1) <= 0,
      }));

  let partyCount = 0;
  let enemyCount = 0;
  const tokens: Token[] = sources.map((source) => {
    const sideIndex = source.isParty ? partyCount++ : enemyCount++;
    const pos = tokenPositions[source.id] ?? defaultPosition(source.isParty, sideIndex);
    return {
      id: source.id,
      name: source.name,
      color: source.isDowned
        ? DOWNED_COLOR
        : source.isParty
          ? PARTY_COLOR
          : ENEMY_COLOR,
      gridX: pos.x,
      gridY: pos.y,
    };
  });

  return (
    <section>
      <h3
        style={{
          fontSize: 14,
          color: "#ccc",
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        Battle Map
      </h3>
      {tokens.length === 0 && (
        <p style={{ color: "#555", fontSize: 12, margin: "0 0 8px" }}>
          Tokens appear here once characters join the world or combat starts.
        </p>
      )}
      <div
        style={{
          background: "#111",
          borderRadius: 6,
          overflow: "hidden",
          display: "inline-block",
        }}
      >
        <Stage width={W} height={H}>
          <Layer>
            <Rect x={0} y={0} width={W} height={H} fill="#1a1a1a" />
            <GridLines />
          </Layer>
          <Layer>
            {tokens.map((t) => (
              <TokenShape key={t.id} token={t} onMove={onTokenMove} />
            ))}
          </Layer>
        </Stage>
      </div>
    </section>
  );
}
