import React from 'react';

const SECTORS_COUNT = 13;
const RADIUS = 42; 

const IMAGES = {
  table: '/images/table.png',
  tableNo13: '/images/table_all_arrows.png',
  letter: '/images/letter.png',
  blitz: '/images/blitz.png',
  superblitz: '/images/superblitz.png',
  arrow: '/images/red_arrow.png',
  volchok: '/images/volchok.png',
};

export function GameTable({ gameState, isAdmin = false, questionTitles = null }) {
  const { current_sector, target_angle, is_spinning, used_questions = [] } = gameState || {};
  const questionTypes = gameState?.question_types || null;
  
  const [rotationAngle, setRotationAngle] = React.useState(0);

  React.useEffect(() => {
    if (target_angle !== null && target_angle !== undefined) {
      
      let targetBaseAngle = (target_angle - 90) % 360;
      if (targetBaseAngle < 0) targetBaseAngle += 360;

      const currentTotalRotation = rotationAngle;
      const currentMod = currentTotalRotation % 360;
      let delta = targetBaseAngle - currentMod;
      
      if (delta <= 0) delta += 360;

      const spins = 5 * 360;
      const finalAngle = currentTotalRotation + delta + spins;
      
      setRotationAngle(finalAngle);
    }
  }, [target_angle]);

  // Синхронизация при сбросе/загрузке
  React.useEffect(() => {
    // Если мы не крутимся (нет активной цели), ставим стрелку туда, где она должна быть
    // Но теперь у нас нет "угла сектора" в явном виде от сервера, есть только current_sector.
    // Придется считать угол сектора самим, чтобы "восстановить" положение.
    // current_sector 1 -> 90 + 1*step
    
    if (target_angle === null && current_sector) {
        const angleStep = 360 / SECTORS_COUNT;
        const sectorAngle = 90 + (current_sector * angleStep);
        
        // Приводим к CSS координатам
        const cssAngle = sectorAngle - 90; 
        setRotationAngle(cssAngle);
    }
  }, [current_sector, target_angle]);

  // Сброс угла в 0..360
  React.useEffect(() => {
    if (!is_spinning && gameState?.spin_duration === 0) {
      setRotationAngle(prev => prev % 360);
    }
  }, [is_spinning, gameState?.spin_duration]);

  // Картинка стола: меняем, если 13 сектор уже сыгран
  const is13Played = used_questions.includes(13);
  const tableImage = is13Played ? IMAGES.tableNo13 : IMAGES.table;

  const renderEnvelopes = () => {
    const envelopes = [];
    for (let i = 1; i < SECTORS_COUNT; i++) {
      if (used_questions.includes(i)) continue;

      const angleStep = 360 / SECTORS_COUNT;
      const angleDeg = 90 + (i * angleStep); 
      const angleRad = (angleDeg * Math.PI) / 180;
      const top = 50 + Math.sin(angleRad) * RADIUS;
      const left = 50 + Math.cos(angleRad) * RADIUS;
      const rotation = angleDeg + 90; 
      const qType = Array.isArray(questionTypes) ? questionTypes[i - 1] : null;
      const envelopeSrc =
        qType === 'blitz'
          ? IMAGES.blitz
          : qType === 'superblitz'
            ? IMAGES.superblitz
            : IMAGES.letter;
      const title = Array.isArray(questionTitles) ? questionTitles[i - 1] : null;

      envelopes.push(
        <div
          key={i}
          className="absolute transition-all group"
          style={{
            top: `${top}%`,
            left: `${left}%`,
            width: '12%',   
            height: '18%',
            transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
          }}
        >
           <img 
             src={envelopeSrc} 
             alt={`Сектор ${i}`}
             className="w-full h-full object-contain drop-shadow-lg"
           />
           {isAdmin && title && (
             <div
               className="pointer-events-none absolute left-1/2 top-0 z-30 w-[220px] -translate-x-1/2 -translate-y-full opacity-0 transition-opacity duration-150 group-hover:opacity-100"
               style={{ transform: `translate(-50%, -100%) rotate(${-rotation}deg)` }}
             >
               <div className="rounded-md bg-slate-950/90 border border-slate-700 px-2 py-1 text-xs text-slate-100 shadow-xl">
                 {title}
               </div>
             </div>
           )}
           {isAdmin && import.meta.env.DEV && (
             <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-black font-bold text-xs md:text-sm">
               {i}
             </span>
           )}
        </div>
      );
    }
    return envelopes;
  };

  return (
    <div className="relative w-full max-w-[800px] aspect-square mx-auto">
      <img 
        src={tableImage} 
        alt="Игровой стол"
        className="w-full h-full object-contain"
      />

      <div className="absolute inset-0">
        {renderEnvelopes()}
      </div>
      
      {/* Стрелка */}
      <div 
        className="absolute top-1/2 left-1/2 w-[5%] h-[60%] transition-transform ease-out"
        style={{
            transformOrigin: '50% 20%',
            transform: `translate(-50%, -20%) rotate(${rotationAngle}deg)`, 
            transitionDuration: `${gameState?.spin_duration || 0}s`
        }}
      >
        <img 
          src={IMAGES.arrow} 
          alt="Стрелка"
          className="w-full h-full object-contain"
        />
      </div>

      {/* Волчок */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[20%] h-[20%]">
        <img 
          src={IMAGES.volchok} 
          alt="Волчок"
          className="w-full h-full object-contain"
        />
      </div>

    </div>
  );
}
