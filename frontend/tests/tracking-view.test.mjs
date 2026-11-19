import assert from 'node:assert/strict';
import test from 'node:test';
import { imagePoint, trailSegments } from '../src/lib/tracking-view.ts';

test('narrow-screen clicks map to original image pixels without changing aspect ratio', () => {
  assert.deepEqual(imagePoint(160, 90, 320, 1920, 1080), [960, 540]);
  assert.deepEqual(imagePoint(320, 180, 320, 1920, 1080), [1920, 1080]);
});

test('trails preserve gaps, explicit player identity and playback boundary', () => {
  const rows = [
    { player_id: 'player_1', source_frame_index: 600, x_ft: 5, y_ft: 25 },
    { player_id: 'player_2', source_frame_index: 600, x_ft: 15, y_ft: 40 },
    { player_id: 'player_1', source_frame_index: 630, x_ft: null, y_ft: null },
    { player_id: 'player_1', source_frame_index: 660, x_ft: 6, y_ft: 26 },
    { player_id: 'player_1', source_frame_index: 690, x_ft: 7, y_ft: 27 },
  ];
  assert.deepEqual(trailSegments(rows, 'player_1', 660), [[[5, 25]], [[6, 26]]]);
  assert.deepEqual(trailSegments(rows, 'player_2', 690), [[[15, 40]]]);
});
