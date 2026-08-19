const fs = require('fs');
const path = require('path');

// Simple 1x1 transparent PNG base64
const transparent1x1 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

const sizes = [16, 32, 72, 96, 128, 144, 152, 192, 384, 512];
const iconDir = path.join(__dirname, '..', 'public', 'icons');

// Create placeholder PNG files (1x1 transparent, will be scaled by browser)
sizes.forEach(size => {
  const buffer = Buffer.from(transparent1x1, 'base64');
  fs.writeFileSync(path.join(iconDir, `icon-${size}x${size}.png`), buffer);
  console.log(`Created icon-${size}x${size}.png (placeholder)`);
});

console.log('All placeholder icons created. Replace with real icons later.');