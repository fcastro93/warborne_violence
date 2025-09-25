# Event Details - Show In-Game Names Instead of Discord Names

## Changes Made to `frontend/warborne_frontend/src/components/EventDetails.js`

### Fixed Lines:
1. **Line 982**: `participant.player?.discord_name` → `participant.player?.in_game_name`
2. **Line 1350**: `participant.discord_name || participant.player?.discord_name` → `participant.player?.in_game_name`
3. **Line 1078**: `getPartyLeader(party)?.player?.discord_name` → `getPartyLeader(party)?.player?.in_game_name`
4. **Line 1096**: `member.player?.discord_name` → `member.player?.in_game_name`
5. **Line 1279**: `selectedParticipant?.player?.discord_name` → `selectedParticipant?.player?.in_game_name`

### What This Fixes:
- Event participants list now shows in-game names (e.g., "Blazing0") instead of Discord names (e.g., "blazing0#0")
- Party leaders display in-game names
- Party member lists show in-game names
- Remove participant dialog shows in-game names

### Result:
Users will now see proper in-game names like:
- "Blazing0" (Offensive Support) with trophy icon
- "Langenschwanz" (Offensive Support)
- "Nemisane" (Offensive Support)
- etc.

Instead of Discord names like:
- "blazing0#0" (Offensive Support)
- "langenschwanz#0" (Offensive Support)
- "nemisane#0" (Offensive Support)
- etc.
