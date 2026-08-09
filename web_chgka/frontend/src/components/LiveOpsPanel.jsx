import { useEffect, useState } from 'react';

import {
  LIVE_OPS_PHASES,
  buildOpenRoundPayload,
  parseBoundedInteger,
} from '../liveOps';
import { socket } from '../socket';
import { phaseLabel, questionKindLabel, responseMessage } from '../uiText';

const buttonClass = 'rounded px-2 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed';

export function LiveOpsPanel({ gameState, addNotification }) {
  const [isOpen, setIsOpen] = useState(false);
  const [znatoki, setZnatoki] = useState(String(gameState?.score?.znatoki ?? 0));
  const [tv, setTv] = useState(String(gameState?.score?.tv ?? 0));
  const [sector, setSector] = useState(String(gameState?.round?.sector ?? gameState?.current_sector ?? 1));
  const [partNumber, setPartNumber] = useState('1');
  const [customSeconds, setCustomSeconds] = useState('60');

  const score = gameState?.score || { znatoki: 0, tv: 0 };
  const usedQuestions = gameState?.used_questions || [];
  const questionTypes = gameState?.question_types || [];
  const round = gameState?.round || null;
  const phase = gameState?.phase;
  const selectedSector = parseBoundedInteger(sector, 1, 13);
  const selectedKind = selectedSector === null ? null : questionTypes[selectedSector - 1];
  const selectedIsBlitz = selectedKind === 'blitz' || selectedKind === 'superblitz';

  useEffect(() => {
    setZnatoki(String(score.znatoki ?? 0));
    setTv(String(score.tv ?? 0));
  }, [score.znatoki, score.tv]);

  useEffect(() => {
    setSector(String(round?.sector ?? gameState?.current_sector ?? 1));
    setPartNumber(String((round?.part_index ?? 0) + 1));
  }, [gameState?.current_sector, round?.part_index, round?.sector]);

  const warn = (message) => {
    addNotification?.({ type: 'warning', message });
  };

  const emitRecovery = (event, payload) => {
    socket.emit(event, payload, (response) => {
      if (response?.ok === false) {
        console.warn('Операция восстановления отклонена:', response.error);
      }
      if (response && response.ok === false && !response.message) {
        warn(responseMessage(response));
      }
    });
  };

  const applyScore = () => {
    const nextZnatoki = parseBoundedInteger(znatoki, 0, 6);
    const nextTv = parseBoundedInteger(tv, 0, 6);
    if (nextZnatoki === null || nextTv === null) {
      warn('Счёт должен быть целым числом от 0 до 6');
      return;
    }
    if (!confirm(`Изменить счёт ${score.znatoki}:${score.tv} → ${nextZnatoki}:${nextTv}?`)) {
      return;
    }
    emitRecovery('admin_set_score', { znatoki: nextZnatoki, tv: nextTv });
  };

  const toggleSector = (sectorId) => {
    const isUsed = usedQuestions.includes(sectorId);
    const action = isUsed ? 'вернуть в игру' : 'пометить сыгранным';
    if (!confirm(`Сектор ${sectorId}: ${action}?`)) return;
    emitRecovery('admin_set_sector_used', { sector: sectorId, used: !isUsed });
  };

  const openRound = () => {
    const payload = buildOpenRoundPayload({
      sector,
      questionTypes,
      partNumber,
    });
    if (!payload) {
      warn('Не удалось определить сектор или часть блица');
      return;
    }
    const partLabel = selectedIsBlitz ? `, часть ${partNumber}/3` : '';
    if (!confirm(`Открыть сектор ${payload.sector}${partLabel} без вращения?`)) return;
    emitRecovery('admin_open_round', payload);
  };

  const forcePhase = (nextPhase) => {
    if (!confirm(`Принудительно перейти «${phaseLabel(phase)}» → «${phaseLabel(nextPhase)}»?`)) return;
    emitRecovery('admin_force_phase', { phase: nextPhase });
  };

  const resetToIntro = () => {
    if (!confirm('Полностью сбросить счёт, сыгранные сектора и начать интро заново?')) {
      return;
    }
    emitRecovery('admin_reset_to_intro');
  };

  const cancelSpin = () => {
    if (!confirm(`Остановить зависшее вращение и вернуться в фазу «${phaseLabel('PRE_ROUND')}»?`)) return;
    emitRecovery('admin_cancel_spin');
  };

  const setTimer = (seconds) => {
    emitRecovery('admin_set_timer', { seconds });
  };

  const applyCustomTimer = () => {
    const seconds = parseBoundedInteger(customSeconds, 1, 600);
    if (seconds === null) {
      warn('Таймер должен быть целым числом от 1 до 600 секунд');
      return;
    }
    setTimer(seconds);
  };

  return (
    <div className="rounded-lg border border-red-900/70 bg-red-950/20">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-bold uppercase tracking-widest text-red-300 hover:bg-red-950/30"
      >
        <span>⚠ Восстановление игры</span>
        <span>{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="border-t border-red-900/60 p-3 flex flex-col gap-4">
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Точный счёт</div>
            <div className="grid grid-cols-[1fr_auto_1fr_auto] gap-2 items-end">
              <label className="text-[10px] text-slate-400">
                Знатоки
                <input
                  type="number"
                  min="0"
                  max="6"
                  value={znatoki}
                  onChange={(event) => setZnatoki(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-white"
                />
              </label>
              <span className="pb-1 text-slate-600">:</span>
              <label className="text-[10px] text-slate-400">
                Телезрители
                <input
                  type="number"
                  min="0"
                  max="6"
                  value={tv}
                  onChange={(event) => setTv(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-white"
                />
              </label>
              <button type="button" onClick={applyScore} className={`${buttonClass} bg-red-800 hover:bg-red-700 text-white`}>
                Применить
              </button>
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Сыгранные / доступные</div>
            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: 13 }, (_, index) => index + 1).map((sectorId) => {
                const isUsed = usedQuestions.includes(sectorId);
                return (
                  <button
                    type="button"
                    key={sectorId}
                    onClick={() => toggleSector(sectorId)}
                    className={`${buttonClass} ${isUsed ? 'bg-red-900 text-red-200' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'}`}
                  >
                    {sectorId}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Открыть раунд</div>
            <div className="flex flex-wrap gap-2">
              <select
                value={sector}
                onChange={(event) => setSector(event.target.value)}
                className="flex-1 rounded border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-white"
              >
                {Array.from({ length: 13 }, (_, index) => index + 1).map((sectorId) => (
                  <option key={sectorId} value={sectorId}>
                    Сектор {sectorId} — {questionKindLabel(questionTypes[sectorId - 1])}
                  </option>
                ))}
              </select>
              {selectedIsBlitz && (
                <select
                  value={partNumber}
                  onChange={(event) => setPartNumber(event.target.value)}
                  className="rounded border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-white"
                >
                  {[1, 2, 3].map((part) => <option key={part} value={part}>Часть {part}</option>)}
                </select>
              )}
              <button type="button" onClick={openRound} className={`${buttonClass} bg-red-800 hover:bg-red-700 text-white`}>
                Открыть
              </button>
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Полный сброс</div>
            <button
              type="button"
              onClick={resetToIntro}
              className={`${buttonClass} w-full bg-red-800 hover:bg-red-700 text-white`}
            >
              Сбросить до интро
            </button>
          </div>

          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Принудительная фаза</div>
            <div className="grid grid-cols-2 gap-1">
              {LIVE_OPS_PHASES.map((nextPhase) => (
                <button
                  type="button"
                  key={nextPhase}
                  disabled={nextPhase !== 'PRE_ROUND' && !round}
                  onClick={() => forcePhase(nextPhase)}
                  className={`${buttonClass} ${phase === nextPhase ? 'bg-red-900 text-red-200' : 'bg-slate-700 text-slate-200 hover:bg-slate-600'}`}
                >
                  {phaseLabel(nextPhase)}
                </button>
              ))}
            </div>
          </div>

          {gameState?.is_spinning && (
            <button type="button" onClick={cancelSpin} className={`${buttonClass} bg-red-700 hover:bg-red-600 text-white`}>
              Остановить зависшее вращение
            </button>
          )}

          {phase === 'DISCUSSION' && (
            <div>
              <div className="text-[10px] uppercase font-bold text-slate-500 mb-2">Таймер восстановления</div>
              <div className="flex flex-wrap gap-1 mb-2">
                {[10, 20, 60].map((seconds) => (
                  <button key={seconds} type="button" onClick={() => setTimer(seconds)} className={`${buttonClass} bg-slate-700 hover:bg-slate-600 text-white`}>
                    {seconds} с
                  </button>
                ))}
                <button type="button" onClick={() => setTimer(null)} className={`${buttonClass} bg-slate-800 hover:bg-slate-700 text-slate-300`}>
                  Остановить таймер
                </button>
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="1"
                  max="600"
                  value={customSeconds}
                  onChange={(event) => setCustomSeconds(event.target.value)}
                  className="flex-1 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white"
                />
                <button type="button" onClick={applyCustomTimer} className={`${buttonClass} bg-slate-700 hover:bg-slate-600 text-white`}>
                  Установить
                </button>
              </div>
            </div>
          )}

          <div>
            <button
              type="button"
              disabled={!gameState?.shared_media}
              onClick={() => socket.emit('admin_hide_media')}
              className={`${buttonClass} w-full bg-slate-700 hover:bg-slate-600 text-white`}
            >
              Скрыть медиа
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
