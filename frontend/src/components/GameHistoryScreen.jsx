import { ADMIN_ENTRY_PATH } from '../entrypoint';
import { GameHistoryPanel } from './GameHistoryPanel';


export function GameHistoryScreen({ socket, addNotification }) {
  return (
    <main className="min-h-screen bg-teal-950 px-4 py-20 text-white">
      <div className="mx-auto w-full max-w-4xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-teal-300">
              Что? Где? Когда?
            </div>
            <h1 className="mt-1 text-3xl font-black text-white">История игр</h1>
          </div>
          <a
            href={ADMIN_ENTRY_PATH}
            className="rounded bg-slate-800 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-300 transition-colors hover:bg-slate-700 hover:text-white"
          >
            К игре
          </a>
        </div>

        <GameHistoryPanel
          socket={socket}
          addNotification={addNotification}
          initiallyOpen
        />
      </div>
    </main>
  );
}
