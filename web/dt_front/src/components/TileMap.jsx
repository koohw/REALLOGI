import React from "react";

const TileMap = ({ mapData, cellSize }) => {
  const getCellStyle = (cell) => {
    switch (cell) {
      case 0:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "rgb(255 255 255)",
        };
      case 1:
        return {
          width: cellSize,
          height: cellSize,
          backgroundImage: "url(/images/box.jpg)", // 이미지를 public/images 폴더에서 참조
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        };
      case 2:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "rgb(224 242 254)",
        };
      default:
        return {
          width: cellSize,
          height: cellSize,
          backgroundColor: "white",
        };
    }
  };

  return (
    <div className="absolute top-0 left-0 w-full h-full">
      {mapData.map((row, y) => (
        <div key={`row-${y}`} className="flex" style={{ height: cellSize }}>
          {row.map((cell, x) => (
            <div key={`cell-${x}-${y}`} style={getCellStyle(cell)} />
          ))}
        </div>
      ))}
    </div>
  );
};

export default TileMap;
