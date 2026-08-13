import { useEffect, useState } from 'react';

import { soundFadeMultiplier } from '../soundFade';


export function useSoundFade(soundControl) {
  const [multiplier, setMultiplier] = useState(() => soundFadeMultiplier(soundControl));

  useEffect(() => {
    const update = () => setMultiplier(soundFadeMultiplier(soundControl));
    update();

    if (soundControl?.mode !== 'fading') return undefined;
    const interval = setInterval(update, 25);
    return () => clearInterval(interval);
  }, [soundControl]);

  return multiplier;
}
