import React from 'react';
import { currentAppPath } from '../appPaths';

export function ScoreBoard({ score }) {
  const { znatoki = 0, tv = 0 } = score || {};
  
  // Формируем имя файла: 60.png, 00.png, 15.png
  const fileName = currentAppPath(`images/table/${znatoki}${tv}.png`);

  return (
    <div className="w-full max-w-[300px] mb-4">
      <img 
        src={fileName} 
        alt={`Счёт ${znatoki}:${tv}`}
        className="w-full h-auto object-contain drop-shadow-2xl"
        onError={(e) => { e.target.style.display = 'none' }} // Скрыть, если картинки нет
      />
    </div>
  );
}
