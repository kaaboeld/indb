// Canvas setup
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const terminal = document.getElementById('terminal');
const hud = document.getElementById('hud');

// Verses
const VERSES = [
    "The LORD is my shepherd; I shall not want.",
    "He maketh me to lie down in green pastures",
    "He leadeth me beside the still waters",
    "He restoreth my soul",
    "Yea, though I walk through the valley of the shadow of death",
    "I will fear no evil: for thou art with me",
    "Thy rod and thy staff they comfort me",
    "Surely goodness and mercy shall follow me all the days of my life"
];

let particles = [];
let mouseX = 0;
let mouseY = 0;

// Proper canvas sizing
function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Mouse tracking
window.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
});

// Particle class
class Particle {
    constructor(text, isDuplicate) {
        this.text = text;
        this.isDuplicate = isDuplicate;

        // Spawn around center
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const angle = Math.random() * Math.PI * 2;
        const dist = 100 + Math.random() * 150;

        this.x = centerX + Math.cos(angle) * dist;
        this.y = centerY + Math.sin(angle) * dist;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.radius = 5;
        this.color = isDuplicate ? '#ff4444' : '#44ff44';
    }

    update() {
        // Gentle drift
        this.vx += (Math.random() - 0.5) * 0.05;
        this.vy += (Math.random() - 0.5) * 0.05;
        this.vx *= 0.98;
        this.vy *= 0.98;

        this.x += this.vx;
        this.y += this.vy;

        // Bounds
        if (this.x < 0) this.x = canvas.width;
        if (this.x > canvas.width) this.x = 0;
        if (this.y < 0) this.y = canvas.height;
        if (this.y > canvas.height) this.y = 0;
    }

    draw() {
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
    }

    distanceTo(x, y) {
        const dx = this.x - x;
        const dy = this.y - y;
        return Math.sqrt(dx * dx + dy * dy);
    }
}

// Animation loop
function animate() {
    // Clear
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw center marker
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, 20, 0, Math.PI * 2);
    ctx.stroke();

    // Update and draw particles
    let nearest = null;
    let nearestDist = 40;

    particles.forEach(p => {
        p.update();
        p.draw();

        const dist = p.distanceTo(mouseX, mouseY);
        if (dist < nearestDist) {
            nearestDist = dist;
            nearest = p;
        }
    });

    // Update HUD
    if (nearest) {
        hud.classList.add('visible');
        hud.style.left = (mouseX + 15) + 'px';
        hud.style.top = (mouseY + 15) + 'px';
        hud.querySelector('.hud-title').textContent = nearest.isDuplicate ? 'DUPLICATE' : 'CANONICAL';
        hud.querySelector('.hud-text').textContent = nearest.text;
    } else {
        hud.classList.remove('visible');
    }

    requestAnimationFrame(animate);
}
animate();

// Logging
function log(msg) {
    const div = document.createElement('div');
    div.className = 'log';
    div.textContent = '[LOG] ' + msg;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;

    // Limit logs
    while (terminal.children.length > 15) {
        terminal.removeChild(terminal.firstChild);
    }
}

// Controls
function addDuplicates() {
    log('Adding 20 duplicate verses...');
    for (let i = 0; i < 20; i++) {
        const verse = VERSES[i % VERSES.length];
        particles.push(new Particle(verse, true));
    }
    log(`Total particles: ${particles.length}`);
}

function addCanonical() {
    log('Adding canonical verse...');
    const verse = VERSES[Math.floor(Math.random() * VERSES.length)];
    particles.push(new Particle(verse, false));
    log(`Added: "${verse.substring(0, 30)}..."`);
}

function removeDuplicates() {
    const before = particles.length;
    const seen = new Set();
    const unique = [];

    particles.forEach(p => {
        if (!seen.has(p.text)) {
            seen.add(p.text);
            p.isDuplicate = false;
            p.color = '#44ff44';
            unique.push(p);
        }
    });

    particles = unique;
    const removed = before - particles.length;

    log(`Removed ${removed} duplicates`);
    log(`${particles.length} unique verses remain`);
}

function showText() {
    log('=== CANONICAL TEXT ===');
    const texts = [...new Set(particles.map(p => p.text))];
    texts.forEach(t => log(t));
    log('======================');
}
