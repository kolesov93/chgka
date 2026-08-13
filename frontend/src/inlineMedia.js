const MEDIA_PLACEHOLDER_PATTERN = /<span class="media-placeholder" data-media-ref="([^"]+)"><\/span>/g;


function escapeHtmlAttribute(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}


export function inlineImagePreviews(html, mediaDescriptors = [], resolvedImages = {}) {
  if (!html) return html;

  const mediaByRef = Object.fromEntries(
    mediaDescriptors.map((descriptor) => [descriptor.media_ref, descriptor]),
  );

  return html.replace(
    MEDIA_PLACEHOLDER_PATTERN,
    (placeholder, mediaRef) => {
      const descriptor = mediaByRef[mediaRef];
      if (descriptor?.type !== 'image') return placeholder;

      const resolution = resolvedImages[mediaRef];
      const name = descriptor.name || 'Изображение';
      const escapedRef = escapeHtmlAttribute(mediaRef);
      const escapedName = escapeHtmlAttribute(name);
      const ready = resolution?.status === 'ready' && resolution.preview?.url;

      let content;
      let label;
      if (ready) {
        content = `<img class="media-inline-preview-image" src="${escapeHtmlAttribute(resolution.preview.url)}" alt="${escapedName}" loading="lazy">`;
        label = `Выбрать изображение ${name}`;
      } else {
        const failed = resolution?.status === 'error';
        const fallback = failed ? 'Изображение недоступно' : 'Загрузка изображения…';
        content = `<span class="media-inline-preview-fallback">${fallback}</span>`;
        label = failed ? `Повторить загрузку изображения ${name}` : `Изображение ${name} загружается`;
      }

      return `<button type="button" class="media-placeholder media-inline-preview" data-media-ref="${escapedRef}" aria-label="${escapeHtmlAttribute(label)}">${content}</button>`;
    },
  );
}
