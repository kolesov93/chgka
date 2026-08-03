export function NotificationsPanel({ notifications, onDismiss }) {
  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className="bg-yellow-500 text-black px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-pulse"
        >
          <span className="font-bold">
            {notification.type === 'player_waiting'
              ? `🔔 ${notification.name} ожидает одобрения`
              : (notification.message || `🔔 ${notification.type}`)}
          </span>
          <button
            onClick={() => onDismiss(notification.id)}
            className="text-black/50 hover:text-black font-bold"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
