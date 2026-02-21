import { useState } from "react";
import { Stage, Layer, Rect, Circle, Text, Line } from "react-konva";
import type Konva from "konva";

const CELL = 50;
const COLS = 10;
const ROWS = 10;
const W = CELL * COLS;
const H = CELL * ROWS;

interface Token {
  id: string;
  name: string;
  color: string;
  gridX: number;
  gridY: number;
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
    e.target.setAttrs({ x: gx * CELL, y: gy * CELL });
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

const DEFAULT_TOKENS: Token[] = [
  { id: "p1", name: "Hero", color: "#3498db", gridX: 1, gridY: 1 },
  { id: "e1", name: "Goblin", color: "#c0392b", gridX: 7, gridY: 7 },
];

export default function BattleMap() {
  const [tokens, setTokens] = useState<Token[]>(DEFAULT_TOKENS);

  const moveToken = (id: string, gx: number, gy: number) => {
    setTokens((prev) =>
      prev.map((t) => (t.id === id ? { ...t, gridX: gx, gridY: gy } : t))
    );
  };

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
              <TokenShape key={t.id} token={t} onMove={moveToken} />
            ))}
          </Layer>
        </Stage>
      </div>
    </section>
  );
}
