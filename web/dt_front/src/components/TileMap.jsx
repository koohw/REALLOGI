import React from "react";

const TileMap = ({ mapData, cellSize }) => {
  const getCellStyle = (cell) => {
    switch (cell) {
      case 0:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "#11263f", // 배경색 변경
        };
      case 1:
        return {
          width: cellSize,
          height: cellSize,
          backgroundImage: "url(/images/box.jpg)",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        };
      case 2:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "#0D1B2A", // 배경색 변경
        };
      default:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "#11263f", // 기본 배경색 변경
        };
    }
  };

  return (
    <div className="absolute top-0 left-0 w-full h-full bg-[#11263f]">
      {/* 전체 배경색 추가 */}
      {mapData.map((row, y) => (
        <div key={`row-${y}`} className="flex" style={{ height: cellSize }}>
          {row.map((cell, x) => (
            <div
              key={`cell-${x}-${y}`}
              style={getCellStyle(cell)}
              className="flex items-center justify-center"
            >
              {cell === 0 && (
                <div className="w-1 h-1 bg-gray-500 opacity-70 rounded-full" />
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default TileMap;
