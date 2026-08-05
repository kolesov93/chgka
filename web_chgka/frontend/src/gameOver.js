function scoreValue(value) {
  return Number.isInteger(value) && value >= 0 ? value : 0;
}


export function gameOverPresentation(score) {
  const znatoki = scoreValue(score?.znatoki);
  const tv = scoreValue(score?.tv);
  const finalScore = `${znatoki}:${tv}`;

  if (znatoki >= 6 && tv >= 6) {
    return {
      winner: null,
      title: 'Счёт требует исправления',
      detail: `Некорректный финальный счёт ${finalScore}`,
    };
  }
  if (znatoki >= 6) {
    return {
      winner: 'znatoki',
      title: 'Победа знатоков',
      detail: `Финальный счёт ${finalScore}`,
    };
  }
  if (tv >= 6) {
    return {
      winner: 'tv',
      title: 'Победа телезрителей',
      detail: `Финальный счёт ${finalScore}`,
    };
  }
  return {
    winner: null,
    title: 'Игра завершена',
    detail: `Финальный счёт ${finalScore}`,
  };
}
