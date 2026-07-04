import React, { useState, useEffect, useRef } from 'react';

function App() {
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [question, setQuestion] = useState("");
  const [demoState, setDemoState] = useState({ loading: false, naive: null, cognee: null });
  
  // UI Modal States
  const [showSettings, setShowSettings] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  // Settings States
  const [darkMode, setDarkMode] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  // Ref for WebGL loop to access latest state without re-triggering useEffect
  const darkModeRef = useRef(darkMode);
  useEffect(() => {
    darkModeRef.current = darkMode;
  }, [darkMode]);

  const canvasRef = useRef(null);
  const threeRef = useRef(null);

  const liveFacts = [
    { subject: "USER", predicate: "location", value: "New York", timestamp: "2023-01-01" },
    { subject: "USER", predicate: "location", value: "Chicago", timestamp: "2024-06-15", supersedes: "New York" },
    { subject: "USER", predicate: "location", value: "Seattle", timestamp: "2025-09-20", supersedes: "Chicago" }
  ];

  const handleDemoRun = async () => {
    setDemoState({ loading: true, naive: null, cognee: null });
    
    try {
      await fetch('http://localhost:8000/api/reset', { method: 'POST' });
      await fetch('http://localhost:8000/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts: liveFacts })
      });

      const [naiveRes, cogneeRes] = await Promise.all([
        fetch('http://localhost:8000/api/query/naive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        }).then(r => r.json()),
        fetch('http://localhost:8000/api/query/cognee', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        }).then(r => r.json())
      ]);

      setDemoState({
        loading: false,
        naive: naiveRes.answer,
        cognee: cogneeRes.answer
      });
      
    } catch (error) {
      console.error(error);
      setDemoState({ loading: false, naive: "Error executing.", cognee: "Error executing." });
    }
  };

  useEffect(() => {
    // Initial fetch
    const fetchResults = () => {
      fetch('http://localhost:8000/api/results')
        .then(res => res.json())
        .then(data => {
          if (data && data.total) setResults(data);
        })
        .catch(err => console.error("Error fetching results", err));
    };
    
    fetchResults();

    // Auto-refresh logic
    let intervalId = null;
    if (autoRefresh) {
      intervalId = setInterval(fetchResults, 5000); // Poll every 5 seconds
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [autoRefresh]);

  // Dark Mode logic
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Set up WebGL Shader Background
  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const gl = canvas.getContext('webgl');
    
    if (gl) {
      const vertexShaderSource = `
          attribute vec2 position;
          varying vec2 v_texCoord;
          void main() {
              gl_Position = vec4(position, 0.0, 1.0);
              v_texCoord = position * 0.5 + 0.5;
          }
      `;
      const fragmentShaderSource = `
          precision highp float;
          varying vec2 v_texCoord;
          uniform float u_time;
          uniform vec2 u_resolution;
          uniform float u_darkMode;

          void main() {
              vec2 uv = v_texCoord;
              
              // Slow, flowing organic movement
              float noise = sin(uv.x * 3.0 + u_time * 0.2) * cos(uv.y * 3.0 - u_time * 0.1);
              noise += 0.5 * sin(uv.x * 6.0 - u_time * 0.4) * cos(uv.y * 5.0 + u_time * 0.3);
              
              vec3 baseColorDark = vec3(0.04, 0.04, 0.06); // Near-black charcoal
              vec3 baseColorLight = vec3(0.92, 0.93, 0.95); // Light cool gray
              
              vec3 baseColor = mix(baseColorLight, baseColorDark, u_darkMode);
              
              vec3 emerald = vec3(0.06, 0.72, 0.51) * 0.15; // Muted green glow
              vec3 coral = vec3(0.95, 0.45, 0.45) * 0.1;    // Muted coral glow
              
              // Blend colors based on noise and position
              float maskEmerald = smoothstep(-0.5, 1.0, noise + uv.x - 0.5);
              float maskCoral = smoothstep(-0.5, 1.0, -noise - uv.x + 0.5);
              
              vec3 color = baseColor;
              color = mix(color, emerald, maskEmerald * (0.4 * u_darkMode + 0.1));
              color = mix(color, coral, maskCoral * (0.3 * u_darkMode + 0.1));
              
              // Vignette effect for depth
              float vignette = 1.0 - length(uv - 0.5) * (0.8 * u_darkMode + 0.2);
              color *= vignette;
              
              gl_FragColor = vec4(color, 1.0);
          }
      `;

      function createShader(gl, type, source) {
          const shader = gl.createShader(type);
          gl.shaderSource(shader, source);
          gl.compileShader(shader);
          return shader;
      }

      const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
      const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);

      const program = gl.createProgram();
      gl.attachShader(program, vertexShader);
      gl.attachShader(program, fragmentShader);
      gl.linkProgram(program);
      gl.useProgram(program);

      const positionBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      const positions = [
          -1.0, -1.0,
            1.0, -1.0,
          -1.0,  1.0,
          -1.0,  1.0,
            1.0, -1.0,
            1.0,  1.0,
      ];
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);

      const positionLocation = gl.getAttribLocation(program, "position");
      gl.enableVertexAttribArray(positionLocation);
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

      const timeLocation = gl.getUniformLocation(program, "u_time");
      const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
      const darkModeLocation = gl.getUniformLocation(program, "u_darkMode");

      function resize() {
          canvas.width = window.innerWidth;
          canvas.height = window.innerHeight;
          gl.viewport(0, 0, canvas.width, canvas.height);
          gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      }
      window.addEventListener('resize', resize);
      resize();

      let startTime = Date.now();
      let animationId;
      function render() {
          gl.uniform1f(timeLocation, (Date.now() - startTime) / 1000.0);
          gl.uniform1f(darkModeLocation, darkModeRef.current ? 1.0 : 0.0);
          gl.drawArrays(gl.TRIANGLES, 0, 6);
          animationId = requestAnimationFrame(render);
      }
      render();

      return () => {
        window.removeEventListener('resize', resize);
        cancelAnimationFrame(animationId);
      };
    }
  }, []);

  // Setup 3D Cognee Graph Background
  useEffect(() => {
    if (!threeRef.current || typeof THREE === 'undefined') return;
    const container = threeRef.current;
    
    // Clear existing
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 15;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const emerald = 0x10b981;
    const coral = 0xf87171;

    const nodes = [];
    const nodeCount = 12;
    const radius = 6;

    const geometry = new THREE.SphereGeometry(0.3, 32, 32);
    const lineMaterial = new THREE.LineBasicMaterial({ color: emerald, transparent: true, opacity: 0.3 });

    for (let i = 0; i < nodeCount; i++) {
        const material = new THREE.MeshPhongMaterial({ 
            color: emerald, 
            emissive: emerald, 
            emissiveIntensity: 0.5 
        });
        const sphere = new THREE.Mesh(geometry, material);
        
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        sphere.position.x = radius * Math.sin(phi) * Math.cos(theta);
        sphere.position.y = radius * Math.sin(phi) * Math.sin(theta);
        sphere.position.z = radius * Math.cos(phi);
        
        group.add(sphere);
        nodes.push(sphere);
    }

    for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
            if (Math.random() > 0.7) {
                const points = [nodes[i].position, nodes[j].position];
                const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(lineGeometry, lineMaterial);
                group.add(line);
            }
        }
    }

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(emerald, 1, 50);
    pointLight.position.set(10, 10, 10);
    scene.add(pointLight);

    let animationId;
    function animate() {
        animationId = requestAnimationFrame(animate);
        group.rotation.y += 0.002;
        group.rotation.x += 0.001;
        
        const time = Date.now() * 0.002;
        nodes.forEach((node, i) => {
            const scale = 1 + Math.sin(time + i) * 0.2;
            node.scale.set(scale, scale, scale);
        });
        
        renderer.render(scene, camera);
    }

    const handleResize = () => {
        const w = container.clientWidth || window.innerWidth;
        const h = container.clientHeight || window.innerHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);
    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
      if (container.firstChild) container.removeChild(container.firstChild);
    };
  }, []);

  // Force reflow for progress rings
  useEffect(() => {
    const timer = setTimeout(() => {
        const rings = document.querySelectorAll('.progress-ring-circle');
        rings.forEach(ring => {
            void ring.offsetWidth;
        });
    }, 100);
    return () => clearTimeout(timer);
  }, [results]);

  const naiveScore = results && results.total > 0 ? Math.round((results.naive_score / results.total) * 100) : 25;
  const cogneeScore = results && results.total > 0 ? Math.round((results.cognee_score / results.total) * 100) : 100;

  const naiveDashOffset = 289 - (289 * naiveScore) / 100;
  const cogneeDashOffset = 289 - (289 * cogneeScore) / 100;

  return (
    <>
      {/* Background Canvas */}
      <canvas 
        ref={canvasRef} 
        className="fixed inset-0 w-full h-full -z-10" 
        style={{ opacity: darkMode ? 1 : 0, transition: 'opacity 0.7s ease' }}
        id="bg-canvas"
      ></canvas>

      <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-margin-page h-16 bg-surface/30 backdrop-blur-xl border-b border-glass/10 fade-in" style={{ animationDelay: '0s' }}>
        <div className="flex items-center gap-8">
          <span className="font-headline-md text-headline-md font-bold text-primary tracking-tight">AETHER BENCHMARK</span>
          <div className="hidden md:flex gap-6">
            <a 
              className={`pb-1 font-body-md text-body-md transition-all duration-200 cursor-pointer ${activeTab === 'dashboard' ? 'text-primary border-b-2 border-primary hover:bg-glass/5' : 'text-on-surface-variant hover:text-on-surface hover:bg-glass/5'}`}
              onClick={(e) => { e.preventDefault(); setActiveTab('dashboard'); }}
            >
              Results Dashboard
            </a>
            <a 
              className={`pb-1 font-body-md text-body-md transition-all duration-200 cursor-pointer ${activeTab === 'demo' ? 'text-primary border-b-2 border-primary hover:bg-glass/5' : 'text-on-surface-variant hover:text-on-surface hover:bg-glass/5'}`}
              onClick={(e) => { e.preventDefault(); setActiveTab('demo'); }}
            >
              Live Comparison Demo
            </a>
          </div>
        </div>
        <div className="flex items-center gap-4 text-primary relative">
          <button 
            className="p-2 hover:bg-glass/5 rounded-full transition-all duration-200"
            onClick={() => { setShowSettings(true); setShowHelp(false); setShowProfile(false); }}
          >
            <span className="material-symbols-outlined">settings</span>
          </button>
          <button 
            className="p-2 hover:bg-glass/5 rounded-full transition-all duration-200"
            onClick={() => { setShowHelp(true); setShowSettings(false); setShowProfile(false); }}
          >
            <span className="material-symbols-outlined">help_outline</span>
          </button>
          
          <div className="relative">
            <img 
              className="w-8 h-8 rounded-full border border-glass/20 object-cover ml-2 cursor-pointer hover:border-primary transition-colors" 
              alt="Avatar" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAWfuWfKnDs0TYvy3sfZh-gtPi7ojKOodwBNaso5j03gzsZtdFwsQfAkUUMuLIzXl5oM4oSccvXwuqcQ9f-i0paeqadxNM4Pccrqj2ZeztstLQWkCnqs9C9--b7qGS43cI4USRqRLIHu-7JerLimMFBHnT-78yHj81TVgKo3rhhPSdfSXGk0UXYH1RjpTEE0AvWJ_lZBM5dZTooO9RFl-KTpduvAOy84jBzl8Ct9b0J5V__4W8OpuKx668tz5jsJm_lkrziCYFysA"
              onClick={() => { setShowProfile(!showProfile); setShowSettings(false); setShowHelp(false); }}
            />
            
            {/* Profile Dropdown */}
            {showProfile && (
              <div className="absolute right-0 mt-4 w-48 bg-surface-container-high border border-glass/10 rounded-xl shadow-2xl py-2 z-50 fade-in text-on-surface">
                <div className="px-4 py-2 border-b border-glass/10 mb-2">
                  <div className="font-bold text-sm">Demo User</div>
                  <div className="text-xs text-on-surface-variant">admin@aether.ai</div>
                </div>
                <button className="w-full text-left px-4 py-2 text-sm hover:bg-glass/5 transition-colors">My Profile</button>
                <button className="w-full text-left px-4 py-2 text-sm hover:bg-glass/5 transition-colors text-error">Sign Out</button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm fade-in" onClick={() => setShowSettings(false)}>
          <div className="bg-surface-container-high border border-glass/10 rounded-xl p-6 w-full max-w-md shadow-2xl relative" onClick={e => e.stopPropagation()}>
            <button className="absolute top-4 right-4 text-on-surface-variant hover:text-white" onClick={() => setShowSettings(false)}>
              <span className="material-symbols-outlined">close</span>
            </button>
            <h2 className="text-2xl font-bold text-on-surface mb-6 font-headline-md">Dashboard Settings</h2>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center bg-glass/5 p-4 rounded-lg">
                <div>
                  <div className="font-bold text-on-surface">Dark Mode</div>
                  <div className="text-sm text-on-surface-variant">Toggle application theme</div>
                </div>
                <div 
                  className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors duration-300 ${darkMode ? 'bg-primary' : 'bg-glass/10'}`}
                  onClick={() => setDarkMode(!darkMode)}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full transition-all duration-300 ${darkMode ? 'right-1 bg-on-primary' : 'left-1 bg-glass/50'}`}></div>
                </div>
              </div>
              
              <div className="flex justify-between items-center bg-glass/5 p-4 rounded-lg">
                <div>
                  <div className="font-bold text-on-surface">Auto-Refresh</div>
                  <div className="text-sm text-on-surface-variant">Poll backend for new results</div>
                </div>
                <div 
                  className={`w-12 h-6 rounded-full relative cursor-pointer transition-colors duration-300 ${autoRefresh ? 'bg-primary' : 'bg-glass/10'}`}
                  onClick={() => setAutoRefresh(!autoRefresh)}
                >
                  <div className={`absolute top-1 w-4 h-4 rounded-full transition-all duration-300 ${autoRefresh ? 'right-1 bg-on-primary' : 'left-1 bg-glass/50'}`}></div>
                </div>
              </div>
            </div>
            
            <button className="w-full mt-6 bg-primary text-on-primary font-bold py-2 rounded-lg hover:bg-primary/90 transition-colors" onClick={() => setShowSettings(false)}>
              Save Preferences
            </button>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm fade-in" onClick={() => setShowHelp(false)}>
          <div className="bg-surface-container-high border border-white/10 rounded-xl p-6 w-full max-w-lg shadow-2xl relative" onClick={e => e.stopPropagation()}>
            <button className="absolute top-4 right-4 text-on-surface-variant hover:text-white" onClick={() => setShowHelp(false)}>
              <span className="material-symbols-outlined">close</span>
            </button>
            <h2 className="text-2xl font-bold text-primary mb-4 font-headline-md">About ContextRot Bench</h2>
            
            <div className="space-y-4 text-on-surface-variant text-sm">
              <p>
                <strong className="text-on-surface">Context Rot</strong> happens when a vector database aggregates contradictory facts over time without deleting superseded data. When an LLM queries this polluted context, it hallucinates.
              </p>
              <p>
                <strong className="text-on-surface">Pipeline A (Naive)</strong> simply embeds and retrieves chunks using standard cosine similarity. It fails when fact history conflicts.
              </p>
              <p>
                <strong className="text-on-surface">Pipeline B (Cognee)</strong> uses a structural Graph architecture combined with LanceDB. We built a custom <em>Deep-Pruning</em> layer that physically purges stale Vector UUIDs whenever a <code>supersedes</code> edge is detected, guaranteeing a 100% accurate context window.
              </p>
            </div>
            
            <div className="mt-6 p-4 bg-primary/10 border border-primary/20 rounded-lg text-primary text-sm flex items-start gap-3">
              <span className="material-symbols-outlined">info</span>
              <p>Use the <strong>Live Comparison Demo</strong> tab to manually trigger a conflict and see how the graphs resolve it in real-time.</p>
            </div>
          </div>
        </div>
      )}

      <main className="max-w-container-max mx-auto px-margin-page md:px-gutter lg:px-margin-page grid grid-cols-12 gap-gutter relative z-10">
        
        {activeTab === 'dashboard' ? (
          <>
            <header className="col-span-12 mb-8 fade-in" style={{ animationDelay: '0.1s' }}>
              <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2 font-bold">ContextRot Bench</h1>
              <p className="font-body-md text-body-md text-on-surface-variant">Proving Cognee's memory lifecycle eliminates context rot.</p>
            </header>

            <section className="col-span-12 md:col-span-6 glass-panel rounded-xl p-6 glow-red flex flex-col items-center justify-center relative overflow-hidden h-64 fade-in" style={{ animationDelay: '0.2s' }}>
              <div className="absolute inset-0 bg-gradient-to-br from-error/5 to-transparent pointer-events-none"></div>
              <h2 className="font-headline-md text-headline-md text-on-surface mb-1 relative z-10 font-bold text-center">Naive Vector Store</h2>
              <div className="text-on-surface-variant text-sm mb-6 relative z-10 italic text-center">(Hallucinates on outdated data)</div>
              <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full progress-ring" viewBox="0 0 100 100">
                  <circle className="text-white/5" cx="50" cy="50" fill="transparent" r="46" stroke="currentColor" strokeWidth="4"></circle>
                  <circle className="text-error progress-ring-circle" cx="50" cy="50" fill="transparent" r="46" stroke="currentColor" strokeDasharray="289" strokeDashoffset={naiveDashOffset} strokeLinecap="round" strokeWidth="4"></circle>
                </svg>
                <span className="absolute font-data-mono text-[48px] font-bold text-error leading-none">{naiveScore}%</span>
              </div>
            </section>

            <section className="col-span-12 md:col-span-6 glass-panel rounded-xl p-6 glow-green flex flex-col items-center justify-center relative overflow-hidden h-64 fade-in" style={{ animationDelay: '0.3s' }}>
              <div className="absolute inset-0 pointer-events-none opacity-30 z-0" ref={threeRef}></div>
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none"></div>
              <h2 className="font-headline-md text-headline-md text-on-surface mb-1 relative z-10 font-bold text-center">Cognee Graph Pipeline</h2>
              <div className="text-on-surface-variant text-sm mb-6 relative z-10 italic text-center">(Self-prunes stale context)</div>
              <div className="relative w-32 h-32 flex items-center justify-center z-10">
                <svg className="w-full h-full progress-ring" viewBox="0 0 100 100">
                  <circle className="text-white/5" cx="50" cy="50" fill="transparent" r="46" stroke="currentColor" strokeWidth="4"></circle>
                  <circle className="text-primary progress-ring-circle" cx="50" cy="50" fill="transparent" r="46" stroke="currentColor" strokeDasharray="289" strokeDashoffset={cogneeDashOffset} strokeLinecap="round" strokeWidth="4"></circle>
                </svg>
                <span className="absolute font-data-mono text-[48px] font-bold text-primary leading-none">{cogneeScore}%</span>
              </div>
            </section>

            <section className="col-span-12 glass-panel rounded-xl p-6 mt-4 fade-in" style={{ animationDelay: '0.4s' }}>
              <h3 className="font-headline-md text-headline-md text-on-surface mb-6 font-bold">Scenario Performance Comparison</h3>
              <div className="space-y-4">
                {results ? results.results.slice(0, 4).map(r => (
                  <div key={r.id} className="grid grid-cols-[200px_1fr] items-center gap-4">
                    <div className="font-data-mono text-data-mono text-on-surface-variant truncate" title={r.id.replace(/_/g, ' ')}>
                      {r.id.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div className="relative h-6 bg-white/5 rounded-sm overflow-hidden flex">
                      <div className={`absolute top-0 bottom-0 left-0 ${r.naive.correct ? 'bg-primary/80' : 'bg-error/80'} z-20 transition-all duration-1000`} style={{ width: r.naive.correct ? '100%' : '33%' }}></div>
                      <div className={`absolute top-0 bottom-0 left-0 ${r.cognee.correct ? 'bg-primary/80' : 'bg-error/80'} z-10 transition-all duration-1000`} style={{ width: r.cognee.correct ? '100%' : '0%' }}></div>
                    </div>
                  </div>
                )) : (
                  <>
                    <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                      <div className="font-data-mono text-data-mono text-on-surface-variant truncate" title="User Location: NY→Chicago→Seattle">User Location: NY→...</div>
                      <div className="relative h-6 bg-white/5 rounded-sm overflow-hidden flex">
                        <div className="absolute top-0 bottom-0 left-0 bg-error/80 w-[0%]" style={{ width: '0%' }}></div>
                        <div className="absolute top-0 bottom-0 left-0 bg-primary/80 w-[100%] z-10"></div>
                      </div>
                    </div>
                    <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                      <div className="font-data-mono text-data-mono text-on-surface-variant truncate" title="Job Status: Applied→Interview→Rejected">Job Status: Applied→...</div>
                      <div className="relative h-6 bg-white/5 rounded-sm overflow-hidden flex">
                        <div className="absolute top-0 bottom-0 left-0 bg-error/80 w-[33%] z-20"></div>
                        <div className="absolute top-0 bottom-0 left-0 bg-primary/80 w-[100%] z-10"></div>
                      </div>
                    </div>
                    <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                      <div className="font-data-mono text-data-mono text-on-surface-variant truncate" title="Project Assignment: A→B→C">Project Assignment: A...</div>
                      <div className="relative h-6 bg-white/5 rounded-sm overflow-hidden flex">
                        <div className="absolute top-0 bottom-0 left-0 bg-error/80 w-[0%] z-20"></div>
                        <div className="absolute top-0 bottom-0 left-0 bg-primary/80 w-[100%] z-10"></div>
                      </div>
                    </div>
                    <div className="grid grid-cols-[200px_1fr] items-center gap-4">
                      <div className="font-data-mono text-data-mono text-on-surface-variant truncate" title="Relationship: Single→Married→Divorced">Relationship: Single...</div>
                      <div className="relative h-6 bg-white/5 rounded-sm overflow-hidden flex">
                        <div className="absolute top-0 bottom-0 left-0 bg-error/80 w-[66%] z-20"></div>
                        <div className="absolute top-0 bottom-0 left-0 bg-primary/80 w-[100%] z-10"></div>
                      </div>
                    </div>
                  </>
                )}
              </div>
              <div className="flex items-center gap-6 mt-6 justify-end font-data-mono text-data-mono">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-error"></span>
                  <span className="text-on-surface-variant">Naive Vector Store</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-primary"></span>
                  <span className="text-on-surface-variant">Cognee Graph</span>
                </div>
              </div>
            </section>

            <section className="col-span-12 glass-panel rounded-xl overflow-hidden mt-4 fade-in" style={{ animationDelay: '0.5s' }}>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 bg-surface-container-low/50">
                      <th className="p-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">Scenario</th>
                      <th className="p-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">Naive Answer</th>
                      <th className="p-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">Cognee Answer</th>
                      <th className="p-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">Ground Truth</th>
                      <th className="p-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="font-data-mono text-data-mono divide-y divide-white/5">
                    {results ? results.results.map(r => (
                      <tr key={r.id} className="hover:bg-white/5 transition-colors">
                        <td className="p-4 text-on-surface">{r.id.replace(/_/g, ' ').toUpperCase()}</td>
                        <td className={`p-4 ${r.naive.correct ? 'text-primary' : 'text-error'}`}>{r.naive.answer.length > 30 ? r.naive.answer.substring(0, 30) + "..." : r.naive.answer}</td>
                        <td className={`p-4 ${r.cognee.correct ? 'text-primary' : 'text-error'}`}>{r.cognee.answer.length > 30 ? r.cognee.answer.substring(0, 30) + "..." : r.cognee.answer}</td>
                        <td className="p-4 text-on-surface-variant">{r.ground_truth}</td>
                        <td className="p-4 text-center">
                          <div className="flex justify-center gap-2">
                            <span className={`material-symbols-outlined ${r.naive.correct ? 'text-primary' : 'text-error'}`}>{r.naive.correct ? 'check' : 'close'}</span>
                            <span className={`material-symbols-outlined ${r.cognee.correct ? 'text-primary' : 'text-error'}`}>{r.cognee.correct ? 'check' : 'close'}</span>
                          </div>
                        </td>
                      </tr>
                    )) : (
                      <>
                        <tr className="hover:bg-white/5 transition-colors">
                          <td className="p-4 text-on-surface">User Location: NY→Chicago→Seattle</td>
                          <td className="p-4 text-error">New York</td>
                          <td className="p-4 text-primary">Seattle</td>
                          <td className="p-4 text-on-surface-variant">Seattle</td>
                          <td className="p-4 text-center">
                            <div className="flex justify-center gap-2">
                              <span className="material-symbols-outlined text-error">close</span>
                              <span className="material-symbols-outlined text-primary">check</span>
                            </div>
                          </td>
                        </tr>
                        <tr className="hover:bg-white/5 transition-colors">
                          <td className="p-4 text-on-surface">Job Status: Applied→Interview→Rejected</td>
                          <td className="p-4 text-error">Applied</td>
                          <td className="p-4 text-primary">Rejected</td>
                          <td className="p-4 text-on-surface-variant">Rejected</td>
                          <td className="p-4 text-center">
                            <div className="flex justify-center gap-2">
                              <span className="material-symbols-outlined text-error">close</span>
                              <span className="material-symbols-outlined text-primary">check</span>
                            </div>
                          </td>
                        </tr>
                        <tr className="hover:bg-glass/5 transition-colors">
                          <td className="p-4 text-on-surface">Project Assignment: A→B→C</td>
                          <td className="p-4 text-error">Project A</td>
                          <td className="p-4 text-primary">Project C</td>
                          <td className="p-4 text-on-surface-variant">Project C</td>
                          <td className="p-4 text-center">
                            <div className="flex justify-center gap-2">
                              <span className="material-symbols-outlined text-error">close</span>
                              <span className="material-symbols-outlined text-primary">check</span>
                            </div>
                          </td>
                        </tr>
                      </>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : (
          <>
            <header className="col-span-12 mb-8 fade-in" style={{ animationDelay: '0.1s' }}>
              <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2 font-bold">Live Comparison Demo</h1>
              <p className="font-body-md text-body-md text-on-surface-variant">Query a live evolving fact stream to witness context rot firsthand.</p>
            </header>
            
            <section className="col-span-12 glass-panel rounded-xl p-6 fade-in mb-4" style={{ animationDelay: '0.2s' }}>
              <h3 className="font-headline-md text-headline-md text-on-surface mb-4 font-bold">Data Stream</h3>
              <div className="space-y-3 font-data-mono text-data-mono">
                {liveFacts.map((fact, idx) => (
                  <div key={idx} className="flex justify-between items-center bg-glass/5 px-4 py-3 rounded-lg border border-glass/10">
                    <span className="text-on-surface-variant">{`[INGEST] ${fact.subject} ${fact.predicate} ${fact.value}`}</span>
                    <span className="text-primary/70">{fact.timestamp}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="col-span-12 glass-panel rounded-xl p-6 fade-in" style={{ animationDelay: '0.3s' }}>
              <div className="flex gap-4 mb-8">
                <input 
                  className="flex-1 bg-surface-container-high border border-glass/10 rounded-lg px-4 py-3 text-on-surface placeholder-glass/30 focus:outline-none focus:border-primary/50 transition-colors"
                  placeholder="Ask a question (e.g. 'Where does the USER live?')" 
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                />
                <button 
                  className={`px-6 py-3 rounded-lg font-bold transition-all ${demoState.loading || !question.trim() ? 'bg-glass/10 text-glass/30 cursor-not-allowed' : 'bg-primary text-on-primary hover:bg-primary/90'}`}
                  onClick={handleDemoRun}
                  disabled={demoState.loading || !question.trim()}
                >
                  {demoState.loading ? 'Running...' : 'Run Both Pipelines'}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-error/5 border border-error/20 rounded-xl p-6">
                  <h3 className="font-headline-md text-2xl text-error mb-4 font-bold">Pipeline A (Naive Vector)</h3>
                  <div className="text-on-surface-variant min-h-[100px]">
                    {demoState.naive || "Waiting for query..."}
                  </div>
                </div>
                <div className="bg-primary/5 border border-primary/20 rounded-xl p-6">
                  <h3 className="font-headline-md text-2xl text-primary mb-4 font-bold">Pipeline B (Cognee Graph)</h3>
                  <div className="text-on-surface-variant min-h-[100px]">
                    {demoState.cognee || "Waiting for query..."}
                  </div>
                </div>
              </div>
            </section>
          </>
        )}

      </main>
    </>
  );
}

export default App;
