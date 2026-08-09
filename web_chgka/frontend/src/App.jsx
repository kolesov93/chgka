import { GameTable } from './components/GameTable';
import { ScoreBoard } from './components/ScoreBoard';
import { LoginScreen } from './components/LoginScreen';
import { WaitingRoom } from './components/WaitingRoom';
import { AdminControls } from './components/AdminControls';
import { AdminQuestionPanel } from './components/AdminQuestionPanel';
import { BlackboxAudio, BlackboxScreen } from './components/BlackboxPresentation';
import { FinalScreen } from './components/FinalScreen';
import { IntroScreen } from './components/IntroScreen';
import { NotificationsPanel } from './components/NotificationsPanel';
import { SharedMediaRenderer } from './components/SharedMediaRenderer';
import { UserHeader } from './components/UserHeader';
import { useDiscussionTimer } from './hooks/useDiscussionTimer';
import { useGameSession } from './hooks/useGameSession';
import { useGameSound } from './hooks/useGameSound';
import { useSocketSoundEvents } from './hooks/useSocketSoundEvents';
import { useSoundFade } from './hooks/useSoundFade';
import { socket } from './socket';
import { phaseLabel } from './uiText';

function App({ entrypoint }) {
  const {
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
  } = useGameSession(entrypoint);

  const soundFadeMultiplier = useSoundFade(gameSettings?.sound_control);
  const effectiveMediaVolume = (gameSettings?.volume ?? 1) * soundFadeMultiplier;
  const { playSound, stopAllSounds } = useGameSound(
    gameState,
    gameSettings?.volume,
    soundFadeMultiplier,
  );
  useSocketSoundEvents(playSound, stopAllSounds);

  const phase = gameState?.phase || 'LOGIN';
  const isAdmin = myRole === 'admin';
  const isIntro = phase === 'INTRO';
  const isPreRound = phase === 'PRE_ROUND';
  const isDiscussion = phase === 'DISCUSSION';
  const isGameOver = phase === 'GAME_OVER';
  const round = gameState?.round || null;
  const showTableForAdmin = isPreRound || !!gameState?.is_spinning;
  const sharedMedia = gameState?.shared_media || null;
  const blackbox = gameState?.blackbox || null;
  const questionPanelKey = `${round?.sector ?? ''}:${round?.kind ?? ''}:${round?.part_index ?? ''}`;

  const { discussionRemaining, markTenSecondsNotified } = useDiscussionTimer({
    isAdmin,
    isDiscussion,
    deadlineMs: gameState?.discussion_deadline_ms,
    addNotification,
    playSound,
  });

  const userHeader = <UserHeader name={myName} role={myRole} onLogout={logout} />;
  const notificationsPanel = (
    <NotificationsPanel notifications={notifications} onDismiss={dismissNotification} />
  );

  if (!isAdmin && !hasJoined) {
    return (
      <LoginScreen
        socket={socket}
        entrypoint={entrypoint}
        sessionNotice={sessionNotice}
      />
    );
  }

  if (!isAdmin && isPending) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center relative">
        {userHeader}
        <div className="text-center">
          <div className="text-6xl mb-6">⏳</div>
          <h1 className="text-3xl font-bold mb-4 text-yellow-500">Ожидание одобрения</h1>
          <p className="text-slate-400 mb-2">Игра уже началась</p>
        </div>
      </div>
    );
  }

  if (phase === 'LOGIN') {
    if (isAdmin) {
      return (
        <>
          {notificationsPanel}
          {userHeader}
          <WaitingRoom
            socket={socket}
            gameState={gameState}
            players={players}
            addNotification={addNotification}
          />
        </>
      );
    }

    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center relative">
        {userHeader}
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4 text-yellow-500">Ожидание начала игры</h1>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen p-4 text-white flex flex-col lg:flex-row lg:items-start lg:justify-center gap-8 relative ${
        isAdmin ? 'bg-indigo-950' : 'bg-slate-900'
      }`}
    >
      {notificationsPanel}
      {userHeader}

      <div className="flex-1 flex flex-col items-center w-full max-w-3xl">
        <div className="w-full flex justify-between items-center mb-4">
          <h1 className="text-xl font-bold text-slate-400 flex items-center gap-2">
            Что? Где? Когда?
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </h1>
          {isAdmin && (
            <div className="text-xs text-slate-500 uppercase font-bold">
              Фаза: {phaseLabel(phase)}
            </div>
          )}
        </div>

        {!isIntro && <ScoreBoard score={gameState?.score} />}

        {blackbox && (
          <div className="w-full">
            <BlackboxAudio
              blackbox={blackbox}
              volume={effectiveMediaVolume}
              onEnded={isAdmin
                ? (payload) => socket.emit('admin_blackbox_ended', payload)
                : null}
            />
          </div>
        )}

        {isIntro ? (
          <div className="mb-4 flex w-full justify-center">
            <IntroScreen
              intro={gameState?.intro}
              isAdmin={isAdmin}
              introHtml={isAdmin ? packInfo?.intro_html : null}
            />
          </div>
        ) : isGameOver ? (
          <div className="w-full flex justify-center mb-4">
            <FinalScreen score={gameState?.score} />
          </div>
        ) : isAdmin && !showTableForAdmin ? (
          <div className="w-full flex justify-center mb-4">
            <div className="w-full">
              <AdminQuestionPanel
                key={questionPanelKey}
                adminQuestion={adminQuestion}
                phase={phase}
                sharedMedia={sharedMedia}
                blackbox={blackbox}
                volume={effectiveMediaVolume}
                addNotification={addNotification}
              />
            </div>
          </div>
        ) : blackbox ? (
          <div className="w-full flex justify-center mb-4">
            <BlackboxScreen />
          </div>
        ) : (
          <div className="w-full flex justify-center mb-4">
            <SharedMediaRenderer media={sharedMedia} volume={effectiveMediaVolume}>
              <GameTable
                gameState={gameState}
                isAdmin={isAdmin}
                questionTitles={packInfo?.question_titles || null}
              />
            </SharedMediaRenderer>
          </div>
        )}
      </div>

      {isAdmin && (
        <AdminControls
          gameState={gameState}
          gameSettings={gameSettings}
          players={players}
          discussionRemaining={discussionRemaining}
          onTenSeconds={markTenSecondsNotified}
          stopAllSounds={stopAllSounds}
          addNotification={addNotification}
        />
      )}
    </div>
  );
}

export default App;
