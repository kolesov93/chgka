# 0011: Inline image previews

Branch: `task/inline-image-previews`
Status: In progress

## Goal

Replace blank image placeholders in the host's question content with compact private thumbnails that can select the existing media control block without showing anything to players.

## Current context

- Question HTML contains opaque `.media-placeholder[data-media-ref]` elements.
- The admin-only `admin_question.media` catalog exposes type, section, order, and name but no path.
- `admin_resolve_media` already exchanges an allowed current-round `media_ref` for a context-bound private `media_id`; only `admin_share_media` changes player presentation.
- The separate media control block already previews and shares resolved images.

## Decisions

- Resolve current image descriptors automatically through the existing `admin_resolve_media` event and reuse the returned private token for the inline thumbnail and the media control block.
- Render a compact, clearly clickable image in the original placeholder position; retain a visible fallback while resolution is pending or fails.
- Clicking a thumbnail only selects it in the existing media control block. It must not emit `admin_share_media`.
- Reset resolved previews when the admin question context changes and ignore late responses from the previous context.
- Keep the backend placeholder HTML, media descriptors, token validation, sharing state, and player UI unchanged.
- Leave audio placeholders and unsupported video behavior unchanged in this task.

## Out of scope

- Video, inline audio players, media queues, automatic sharing, token persistence, backend thumbnail generation, image editing, and Markdown sanitization.

## Verification

- Frontend unit coverage for turning resolved image refs into safe inline preview markup while preserving unresolved and non-image placeholders.
- Frontend production build.
- Focused admin/player browser smoke using sample question 02: the admin sees the thumbnail, clicking it selects the existing control block, and players continue to see the table until `Показать игрокам` is pressed.
