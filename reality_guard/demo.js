// INDB - Scrollytelling Logic V5.3
// FEATURES: Matrix Stats Animation, Multiplier, Smooth Counters, CLEAN UI (No Fill)

const API_URL = 'http://localhost:8003';

const demo = {
    cards: [],
    events: [],
    scrollProgress: 0,

    // Stats tracking (displayed val for lerp)
    stats: {
        raw: 0,
        fusion: 0,
        truth: 0
    },

    // Config
    GHOST_LIMIT: 3,
    DEMO_MULTIPLIER: 142, // Visual scale factor

    init() {
        window.addEventListener('scroll', () => {
            const h = document.documentElement.scrollHeight - window.innerHeight;
            const s = window.scrollY;
            this.scrollProgress = Math.min(1, Math.max(0, s / h));
            // UI updates moved to animate() loop for 60fps sync w/o lag
        });

        this.loadEvents();
        this.animate();
    },

    updateScrollUI() {
        // UI SYNC: Update DOM elements in animation loop to prevent lag
        const line = document.querySelector('.progress-line');
        const dot = document.querySelector('.progress-indicator');
        // removed fill logic

        if (line && dot) {
            // Calculate position (5% to 95%)
            const pct = this.scrollProgress * 90 + 5;
            dot.style.top = `${pct}%`;
        }

        // Narrative visibility
        document.querySelectorAll('.scroll-section').forEach((section, idx) => {
            const rect = section.getBoundingClientRect();
            const center = window.innerHeight / 2;
            const block = section.querySelector('.narrative-block');
            if (block) {
                if (rect.top < center + 200 && rect.bottom > center - 200) {
                    block.classList.add('visible');
                } else {
                    block.classList.remove('visible');
                }
            }
        });
    },

    updateStatsLogic() {
        const p = this.scrollProgress;

        // --- CALCULATE TARGETS ---
        const totalBase = this.events.length + this.events.reduce((acc, e) => acc + (e.fusion_count || 0), 0);
        const totalRawTarget = totalBase * this.DEMO_MULTIPLIER;

        const totalFusionBase = this.events.reduce((acc, e) => acc + (e.fusion_count || 0), 0);
        const totalFusionTarget = totalFusionBase * this.DEMO_MULTIPLIER;

        // 1. Raw Input Target (Ramps up 0.0 -> 0.4)
        let targetRaw = 0;
        if (p < 0.4) {
            targetRaw = totalRawTarget * (p / 0.4);
        } else {
            targetRaw = totalRawTarget;
        }

        // 2. Fusion Ops Target (Ramps up 0.4 -> 0.8)
        let targetFusion = 0;
        if (p > 0.4 && p < 0.8) {
            const fp = (p - 0.4) / 0.4;
            targetFusion = totalFusionTarget * fp;
        } else if (p >= 0.8) {
            targetFusion = totalFusionTarget;
        }

        // --- SMOOTH LERP ---
        this.stats.raw += (targetRaw - this.stats.raw) * 0.1;
        this.stats.fusion += (targetFusion - this.stats.fusion) * 0.1;

        // --- UI UPDATES ---
        const rawEl = document.getElementById('stat-raw');
        const fusEl = document.getElementById('stat-fusion');
        if (rawEl) rawEl.textContent = Math.floor(this.stats.raw).toLocaleString();
        if (fusEl) fusEl.textContent = Math.floor(this.stats.fusion).toLocaleString();

        // 3. CPU Status
        const cpuEl = document.getElementById('stat-cpu');
        if (cpuEl) {
            if (p < 0.5) {
                cpuEl.textContent = "HIGH (INGESTING)";
                cpuEl.className = "stat-value text-red-500";
            } else if (p < 0.8) {
                cpuEl.textContent = "OPTIMIZING...";
                cpuEl.className = "stat-value text-orange-500";
            } else {
                cpuEl.textContent = "0% (IDLE)";
                cpuEl.className = "stat-value text-blue-400";
            }
        }

        // 4. Final Truth Stats
        const finalDiv = document.getElementById('final-stats');
        if (finalDiv) {
            if (p > 0.85) {
                finalDiv.style.opacity = 1;
                // Truth count is just unique events * multiplier
                const truthCount = this.events.length * this.DEMO_MULTIPLIER;
                document.getElementById('stat-truth').textContent = Math.floor(truthCount).toLocaleString();

                // Efficiency
                const eff = totalBase > 0 ? ((totalBase - this.events.length) / totalBase * 100).toFixed(1) : "0.0";
                document.getElementById('stat-eff').textContent = `${eff}%`;
            } else {
                finalDiv.style.opacity = 0;
            }
        }
    },

    async loadEvents() {
        try {
            const response = await fetch(`${API_URL}/api/v2/events?limit=20`);
            const json = await response.json();
            this.events = json.data || [];
            this.createVisuals();
            // Animation loop handles UI updates
        } catch (e) {
            console.error(e);
        }
    },

    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
        }
        return hash;
    },

    createVisuals() {
        const world = document.getElementById('world');
        if (!world) return;
        world.innerHTML = '';
        this.cards = [];

        this.events.forEach((event, i) => {
            const loc = (event.location || 'Unknown').split(' ')[0];
            const suitMap = { 'London': '♠', 'Amsterdam': '♥', 'Rotterdam': '♦' };
            const fallbackSuits = ['♠', '♥', '♦', '♣'];
            const suit = suitMap[loc] || fallbackSuits[Math.abs(this.hashCode(event.id)) % 4];

            const isRed = suit === '♥' || suit === '♦';

            const idHash = Math.abs(this.hashCode(event.id));
            const rankVal = idHash % 13;
            const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
            const rankChar = ranks[rankVal];

            const fusion = event.fusion_count || 0;
            const ghostCount = Math.min(fusion, this.GHOST_LIMIT);

            this.spawnCard(world, event, i, rankChar, suit, isRed, true);

            for (let g = 0; g < ghostCount; g++) {
                this.spawnCard(world, event, i, rankChar, suit, isRed, false, g);
            }
        });
    },

    spawnCard(container, event, index, rank, suit, isRed, isPrimary, ghostIndex = 0) {
        const el = document.createElement('div');
        el.className = `card ${isRed ? 'red' : 'black'} ${!isPrimary ? 'ghost' : ''}`;

        let displayData = '';
        const anchors = event.raw_data_anchor || [];

        if (isPrimary) {
            displayData = anchors.slice(0, 3).join('<br>').substring(0, 50);
            if (anchors.length > 3) displayData += '...';
        } else {
            const specificAnchor = anchors[ghostIndex] || anchors[anchors.length - 1];
            if (specificAnchor) {
                displayData = `RAW SEGMENT:<br>${specificAnchor.substring(0, 40)}`;
            } else {
                displayData = `COMPRESSED SIG::<br>${event.id.substring(0, 8)}`;
            }
        }

        el.innerHTML = `
            <div class="card-inner">
                <div class="card-corner">
                    <div>${rank}</div>
                    <div>${suit}</div>
                </div>
                <div class="card-body">
                    ${suit}
                </div>
                <div class="data-rows font-mono">
                    ${displayData}
                </div>
                <div class="card-corner" style="transform: rotate(180deg)">
                    <div>${rank}</div>
                    <div>${suit}</div>
                </div>
            </div>
        `;

        if (isPrimary) {
            el.onclick = () => this.showHud(event);
        }

        container.appendChild(el);

        this.cards.push({
            element: el,
            isPrimary: isPrimary,
            parentId: index,

            x: 0, y: 0, z: -1000,
            rotX: 0, rotY: 0, rotZ: 0,

            randX: Math.random() - 0.5,
            randY: Math.random() - 0.5,
            randZ: Math.random() - 0.5,

            tx: 0, ty: 0, tz: 0,
            trotX: 0, trotY: 0, trotZ: 0
        });
    },

    animate() {
        // Core Animation Loop
        const p = this.scrollProgress;

        // Update Stats UI (Smooth Lerp)
        this.updateStatsLogic();

        // Update Scroll UI (Line/Dot/Fill)
        this.updateScrollUI();

        this.cards.forEach((card, i) => {
            const time = Date.now() * 0.001;

            // 1. CHAOS
            if (p < 0.4) {
                const chaosLevel = Math.min(p * 3, 1);
                const spread = 1200 * chaosLevel;
                const startZ = -card.parentId * 2;

                card.tx = card.randX * spread;
                card.ty = card.randY * spread * 0.6;
                card.tz = (startZ * (1 - chaosLevel)) + (card.randZ * 800 * chaosLevel);

                card.trotX = card.randX * 720 * chaosLevel;
                card.trotY = card.randY * 720 * chaosLevel;
                card.trotZ = card.randZ * 720 * chaosLevel;
            }
            // 2. STRUCTURE
            else if (p < 0.6) {
                const cols = 5;
                const row = Math.floor(card.parentId / cols);
                const col = card.parentId % cols;
                const gridX = (col - 2) * 200;
                const gridY = (row - 2) * 240;

                if (card.isPrimary) {
                    card.tx = gridX; card.ty = gridY; card.tz = 0;
                    card.trotX = 0; card.trotY = 0; card.trotZ = 0;
                } else {
                    card.tx = gridX + card.randX * 150;
                    card.ty = gridY + card.randY * 150;
                    card.tz = 50;
                    card.trotX = card.randX * 20; card.trotY = card.randY * 20; card.trotZ = 0;
                }
            }
            // 3. FUSION
            else if (p < 0.8) {
                const fusionProgress = (p - 0.6) / 0.2;
                const cols = 5;
                const row = Math.floor(card.parentId / cols);
                const col = card.parentId % cols;
                const gridX = (col - 2) * 200;
                const gridY = (row - 2) * 240;

                card.tx = gridX; card.ty = gridY;
                card.trotX = 0; card.trotY = 0; card.trotZ = 0;

                if (card.isPrimary) {
                    card.tz = 0;
                } else {
                    card.tx = gridX + (card.randX * 150 * (1 - fusionProgress));
                    card.ty = gridY + (card.randY * 150 * (1 - fusionProgress));
                    card.tz = 50 * (1 - fusionProgress);
                    card.trotZ += 5;
                }
            }
            // 4. TRUTH
            else {
                if (card.isPrimary) {
                    const cols = 5;
                    const row = Math.floor(card.parentId / cols);
                    const col = card.parentId % cols;
                    card.tx = (col - 2) * 160;
                    card.ty = (row - 2) * 200;
                    card.tz = 300;
                    card.ty += Math.sin(time + i) * 5;
                } else {
                    card.tx = 0; card.ty = 0; card.tz = 0;
                }
            }

            // PHYSICS
            const lerp = 0.1;
            card.x += (card.tx - card.x) * lerp;
            card.y += (card.ty - card.y) * lerp;
            card.z += (card.tz - card.z) * lerp;
            card.rotX += (card.trotX - card.rotX) * lerp;
            card.rotY += (card.trotY - card.rotY) * lerp;
            card.rotZ += (card.trotZ - card.rotZ) * lerp;

            // RENDER
            let scale = 1;
            let opacity = 1;

            if (!card.isPrimary) {
                if (p > 0.6 && p < 0.8) {
                    const fp = (p - 0.6) / 0.2;
                    opacity = 1 - fp;
                    scale = 1 - (fp * 0.5);
                } else if (p >= 0.8) {
                    opacity = 0; scale = 0;
                } else {
                    opacity = 0.6;
                }
            }

            card.element.style.transform =
                `translate3d(${card.x}px, ${card.y}px, ${card.z}px) ` +
                `rotateX(${card.rotX}deg) rotateY(${card.rotY}deg) rotateZ(${card.rotZ}deg) ` +
                `scale(${scale})`;
            card.element.style.opacity = opacity;
        });

        requestAnimationFrame(() => this.animate());
    },

    showHud(event) {
        const hud = document.getElementById('hud');
        if (!hud) return;
        hud.style.display = 'block';
        document.getElementById('hud-id').textContent = event.id.substring(0, 8);
        document.getElementById('hud-loc').textContent = event.location;
        document.getElementById('hud-fusion').textContent = event.fusion_count;
        document.getElementById('hud-payload').textContent = (event.raw_data_anchor || []).join(', ');
    }
};

demo.init();
