import React from 'react';

const SECTORS_COUNT = 13;
const RADIUS = 42; // Радиус расположения конвертов (в % от ширины стола)

// Картинки (пути относительно папки public)
const IMAGES = {
  table: '/images/table.png',
  tableNo13: '/images/table_all_arrows.png',
  letter: '/images/letter.png',
  blitz: '/images/blitz.png',
  superblitz: '/images/superblitz.png',
  arrow: '/images/red_arrow.png',
  volchok: '/images/volchok.png',
};

export function GameTable({ gameState }) {
  const { current_sector, target_sector, is_spinning, used_questions = [] } = gameState || {};
  
  // Угол поворота стрелки
  const [rotationAngle, setRotationAngle] = React.useState(0);

  React.useEffect(() => {
    if (target_sector) {
      const angleStep = 360 / SECTORS_COUNT;
      const targetAngleRaw = 90 + (target_sector * angleStep);
      // Поправка на начальное положение стрелки: она смотрит ВНИЗ (90 градусов в геометрии), 
      // но в CSS rotate(0) это её дефолтное положение.
      // Если мы хотим, чтобы она указывала на targetAngleRaw (который отсчитывается от 3 часов),
      // нам нужно учесть, что 0 градусов CSS = 90 градусов геометрии (6 часов).
      // Значит rotation = targetAngleRaw - 90.
      
      // Добавим 5 оборотов (1800 градусов) + случайный разброс (пока убрал)
      const finalAngle = (targetAngleRaw - 90) + 1800; 
      
      setRotationAngle(finalAngle);
    }
  }, [target_sector]);

  // Определяем, какую картинку стола показывать (с 13 сектором или без)
  // Пока заглушка, берем обычный стол
  const tableImage = IMAGES.table;

  // Генерация позиций конвертов
  const renderEnvelopes = () => {
    const envelopes = [];
    for (let i = 1; i < SECTORS_COUNT; i++) {
      // Если вопрос уже сыгран - не рисуем конверт
      if (used_questions.includes(i)) continue;

      // Угол для i-го сектора
      // В оригинале: 1.5 * PI - (2 * PI) / 13 * i
      // Ноль в CSS (transform: rotate) обычно справа (3 часа), 
      // а нам нужно расположить их так, чтобы сектор 1 был "сразу после 12 часов".
      // Подгоним угол экспериментально или математически.
      
      // Шаг угла в градусах
      const angleStep = 360 / SECTORS_COUNT;
      // Сдвиг, чтобы 1-й сектор был на своем месте
      const angleDeg = 90 + (i * angleStep); 

      // Позиция через тригонометрию (для absolute positioning внутри квадратного стола)
      // Центр стола = 50%, 50%
      // X = 50 + cos(a) * R
      // Y = 50 + sin(a) * R
      const angleRad = (angleDeg * Math.PI) / 180;
      const top = 50 + Math.sin(angleRad) * RADIUS;
      const left = 50 + Math.cos(angleRad) * RADIUS;

      // Поворот самого конверта, чтобы он "смотрел" в центр или от центра
      const rotation = angleDeg + 90; 

      envelopes.push(
        <div
          key={i}
          className="absolute transition-all"
          style={{
            top: `${top}%`,
            left: `${left}%`,
            width: '12%',   // Размер в % от стола (было фиксировано)
            height: '18%',  // Пропорция конверта
            transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
          }}
        >
           <img 
             src={IMAGES.letter} 
             alt={`Sector ${i}`}
             className="w-full h-full object-contain drop-shadow-lg"
           />
           {/* Номер сектора (виден только в режиме разработки) */}
           {import.meta.env.DEV && (
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
      {/* Фоновый стол */}
      <img 
        src={tableImage} 
        alt="Game Table" 
        className="w-full h-full object-contain"
      />

      {/* Слой с конвертами */}
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
          alt="Arrow" 
          className="w-full h-full object-contain"
        />
      </div>

      {/* Волчок (по центру)  */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[20%] h-[20%]">
        <img 
          src={IMAGES.volchok} 
          alt="Volchok" 
          className="w-full h-full object-contain"
        />
      </div>

    </div>
  );
}

