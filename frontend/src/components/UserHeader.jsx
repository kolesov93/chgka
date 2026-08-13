export function UserHeader({ name, role, onLogout }) {
  return (
    <div className="absolute top-4 right-4 flex items-center gap-4">
      {name && (
        <div
          className="max-w-[55vw] truncate text-right text-sm font-bold text-slate-400"
          title={role === 'admin' ? 'Ведущий' : name}
        >
          {role === 'admin' ? <span className="text-yellow-500">Ведущий</span> : name}
        </div>
      )}
      <button
        onClick={onLogout}
        className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 py-2 px-3 rounded font-bold uppercase tracking-wider transition-colors"
      >
        Выход
      </button>
    </div>
  );
}
