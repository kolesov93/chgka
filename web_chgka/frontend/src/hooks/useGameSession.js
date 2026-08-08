import { useCallback, useEffect, useState } from 'react';
import { socket } from '../socket';
import {
  ADMIN_TOKEN_KEY,
  PLAYER_TOKEN_KEY,
  getAdminExpiryMs,
  getExpiredAdminSession,
  getSessionRestorePayload,
  saveAdminToken,
} from '../session';

export function useGameSession() {
  const [gameState, setGameState] = useState(null);
  const [gameSettings, setGameSettings] = useState({ volume: 1.0, sound_control: null });
  const [players, setPlayers] = useState([]);
  const [myRole, setMyRole] = useState('player');
  const [myName, setMyName] = useState('');
  const [packInfo, setPackInfo] = useState(null);
  const [adminQuestion, setAdminQuestion] = useState(null);
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [hasJoined, setHasJoined] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [sessionNotice, setSessionNotice] = useState('');
  const [adminExpiresAtMs, setAdminExpiresAtMs] = useState(null);

  const expireAdminSession = useCallback((data) => {
    const expired = getExpiredAdminSession(data);
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setMyRole(expired.role);
    setMyName(expired.name);
    setHasJoined(expired.hasJoined);
    setIsPending(expired.isPending);
    setPackInfo(expired.packInfo);
    setAdminQuestion(expired.adminQuestion);
    setSessionNotice(expired.notice);
    setAdminExpiresAtMs(null);
  }, []);

  useEffect(() => {
    if (adminExpiresAtMs === null) return undefined;

    const delayMs = Math.max(0, adminExpiresAtMs - Date.now());
    const timeoutId = setTimeout(() => expireAdminSession(), delayMs);
    return () => clearTimeout(timeoutId);
  }, [adminExpiresAtMs, expireAdminSession]);

  const addNotification = useCallback((notification) => {
    const id = Date.now();
    setNotifications((current) => [...current, { id, ...notification }]);
    setTimeout(() => {
      setNotifications((current) => current.filter((item) => item.id !== id));
    }, 5000);
  }, []);

  const dismissNotification = useCallback((id) => {
    setNotifications((current) => current.filter((item) => item.id !== id));
  }, []);

  useEffect(() => {
    window.authenticateAdmin = (password) => {
      socket.emit('authenticate_admin', { password });
    };
    return () => {
      delete window.authenticateAdmin;
    };
  }, []);

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);

      const restorePayload = getSessionRestorePayload(localStorage);
      if (restorePayload) socket.emit('restore_session', restorePayload);
    }

    function onDisconnect() {
      setIsConnected(false);
      setMyRole('player');
      setMyName('');
    }

    function onStateUpdate(newState) {
      if (!newState) {
        setGameState(newState);
        return;
      }
      const intro = newState.intro
        ? { ...newState.intro, received_at_ms: Date.now() }
        : null;
      const blackbox = newState.blackbox
        ? { ...newState.blackbox, received_at_ms: Date.now() }
        : null;
      setGameState({ ...newState, intro, blackbox });
    }

    function onRoleUpdate(data) {
      if (data?.role) {
        setMyRole(data.role);
        if (data.role !== 'admin') setAdminExpiresAtMs(null);
      }
    }

    function onSettingsUpdate(newSettings) {
      if (newSettings) {
        const soundControl = newSettings.sound_control
          ? { ...newSettings.sound_control, received_at_ms: Date.now() }
          : undefined;
        setGameSettings((current) => ({
          ...current,
          ...newSettings,
          ...(soundControl ? { sound_control: soundControl } : {}),
        }));
      }
    }

    function onPlayersUpdate(data) {
      if (data?.players) setPlayers(data.players);
    }

    function onAuthSuccess(data) {
      saveAdminToken(localStorage, data.token);
      setAdminExpiresAtMs(getAdminExpiryMs(data));
      setSessionNotice('');
    }

    function onAuthFailed(data) {
      console.error('[Auth] Failed:', data.message || 'Неверный пароль');
      localStorage.removeItem(ADMIN_TOKEN_KEY);
      setAdminExpiresAtMs(null);
    }

    function onAuthRestored(data) {
      console.log('[Auth] Session restored successfully');
      setAdminExpiresAtMs(getAdminExpiryMs(data));
      setSessionNotice('');
    }

    function onAuthExpired(data) {
      expireAdminSession(data);
    }

    function onJoinSuccess(data) {
      if (data.token) localStorage.setItem(PLAYER_TOKEN_KEY, data.token);
      if (data.name) setMyName(data.name);
      setIsPending(false);
      setHasJoined(true);
      setSessionNotice('');
    }

    function onJoinPending(data) {
      if (data.token) localStorage.setItem(PLAYER_TOKEN_KEY, data.token);
      if (data.name) setMyName(data.name);
      setIsPending(true);
      setHasJoined(true);
      setSessionNotice('');
    }

    function onKicked(data) {
      localStorage.removeItem(PLAYER_TOKEN_KEY);
      setGameState(null);
      setMyRole('player');
      setMyName('');
      setHasJoined(false);
      setIsPending(false);

      alert(data.message || 'Вы были отключены');
      socket.disconnect();
      socket.connect();
    }

    function onPackInfo(data) {
      if (data?.pack) setPackInfo(data.pack);
    }

    function onAdminQuestion(data) {
      setAdminQuestion(data || null);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('state_update', onStateUpdate);
    socket.on('role_update', onRoleUpdate);
    socket.on('settings_update', onSettingsUpdate);
    socket.on('players_update', onPlayersUpdate);
    socket.on('auth_success', onAuthSuccess);
    socket.on('auth_failed', onAuthFailed);
    socket.on('auth_restored', onAuthRestored);
    socket.on('auth_expired', onAuthExpired);
    socket.on('join_success', onJoinSuccess);
    socket.on('join_pending', onJoinPending);
    socket.on('kicked', onKicked);
    socket.on('admin_notification', addNotification);
    socket.on('pack_info', onPackInfo);
    socket.on('admin_question', onAdminQuestion);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('state_update', onStateUpdate);
      socket.off('role_update', onRoleUpdate);
      socket.off('settings_update', onSettingsUpdate);
      socket.off('players_update', onPlayersUpdate);
      socket.off('auth_success', onAuthSuccess);
      socket.off('auth_failed', onAuthFailed);
      socket.off('auth_restored', onAuthRestored);
      socket.off('auth_expired', onAuthExpired);
      socket.off('join_success', onJoinSuccess);
      socket.off('join_pending', onJoinPending);
      socket.off('kicked', onKicked);
      socket.off('admin_notification', addNotification);
      socket.off('pack_info', onPackInfo);
      socket.off('admin_question', onAdminQuestion);
    };
  }, [addNotification, expireAdminSession]);

  const logout = useCallback(() => {
    if (!confirm('Вы действительно хотите выйти?')) return;

    socket.emit('leave_game');
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(PLAYER_TOKEN_KEY);
    socket.disconnect();

    setGameState(null);
    setMyRole('player');
    setMyName('');
    setHasJoined(false);
    setPlayers([]);
    setIsConnected(false);
    setPackInfo(null);
    setAdminQuestion(null);
    setSessionNotice('');
    setAdminExpiresAtMs(null);

    socket.connect();
  }, []);

  return {
    gameState,
    gameSettings,
    players,
    myRole,
    myName,
    packInfo,
    adminQuestion,
    isConnected,
    hasJoined,
    isPending,
    sessionNotice,
    notifications,
    addNotification,
    dismissNotification,
    logout,
  };
}
