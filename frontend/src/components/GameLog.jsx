import React, { useEffect, useRef } from 'react';

export function GameLog({ logs = [] }) {
  return (
    <div className="w-full h-40 bg-black/80 rounded-lg border border-slate-700 p-2 overflow-y-auto font-mono text-xs text-green-400 shadow-inner">
      {logs.length === 0 && <div className="text-slate-600 italic">Лог пуст...</div>}
      {logs.map((entry, idx) => (
        <div key={idx} className="mb-1 border-b border-slate-800 pb-1 last:border-0">
          {entry}
        </div>
      ))}
    </div>
  );
}

