import React, { useState, useEffect, useRef } from 'react';

// Physics Map 세계 지도 시각화
const PhysicsMapGlobal = () => {
  const canvasRef = useRef(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const animationRef = useRef(null);
  const timeRef = useRef(0);

  // 샘플 데이터 (Physics Map 결과 기반)
  const nodes = [
    { id: 'P03', name: 'CONTROLLER', lat: 37.5665, lon: 126.978, value: 182886563, color: '#00ff88', role: 'CONTROLLER' },
    { id: 'P05', name: 'BUILDER', lat: 35.6762, lon: 139.6503, value: 175282188, color: '#00ccff', role: 'BUILDER' },
    { id: 'P11', name: 'CONNECTOR', lat: 22.3193, lon: 114.1694, value: 175282188, color: '#ffcc00', role: 'CONNECTOR' },
    { id: 'P01', name: 'RAINMAKER', lat: 1.3521, lon: 103.8198, value: 175282188, color: '#ff6600', role: 'RAINMAKER' },
    { id: 'P07', name: 'PARTNER', lat: 40.7128, lon: -74.006, value: 50000000, color: '#9966ff', role: 'PARTNER' },
    { id: 'P08', name: 'INVESTOR', lat: 51.5074, lon: -0.1278, value: 80000000, color: '#ff3366', role: 'INVESTOR' },
    { id: 'P12', name: 'SUPPLIER', lat: -33.8688, lon: 151.2093, value: 30000000, color: '#33cccc', role: 'SUPPLIER' },
  ];

  // 돈 흐름 (시너지 연결)
  const links = [
    { source: 'P03', target: 'P11', value: 11406562, type: 'synergy' },
    { source: 'P03', target: 'P05', value: 3802187, type: 'synergy' },
    { source: 'P01', target: 'P03', value: 3802187, type: 'synergy' },
    { source: 'P07', target: 'P01', value: 15000000, type: 'flow' },
    { source: 'P08', target: 'P03', value: 25000000, type: 'investment' },
    { source: 'P12', target: 'P05', value: 8000000, type: 'supply' },
  ];

  // 위경도 → 화면 좌표 변환 (메르카토르 투영)
  const latLonToXY = (lat, lon, width, height) => {
    const x = ((lon + 180) / 360) * width;
    const latRad = (lat * Math.PI) / 180;
    const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2));
    const y = (height / 2) - (width * mercN) / (2 * Math.PI);
    return { x, y };
  };

  // 세계 지도 경계 그리기 (간단한 대륙 윤곽)
  const drawWorldMap = (ctx, width, height) => {
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, width, height);

    // 격자
    ctx.strokeStyle = '#1a2a3a';
    ctx.lineWidth = 0.5;
    for (let lon = -180; lon <= 180; lon += 30) {
      const { x } = latLonToXY(0, lon, width, height);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let lat = -60; lat <= 80; lat += 20) {
      const { y } = latLonToXY(lat, 0, width, height);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // 간단한 대륙 (사각형으로 표현)
    const continents = [
      { name: 'North America', x1: -170, y1: 70, x2: -50, y2: 15 },
      { name: 'South America', x1: -85, y1: 15, x2: -35, y2: -55 },
      { name: 'Europe', x1: -10, y1: 70, x2: 40, y2: 35 },
      { name: 'Africa', x1: -20, y1: 35, x2: 55, y2: -35 },
      { name: 'Asia', x1: 40, y1: 75, x2: 180, y2: 5 },
      { name: 'Australia', x1: 110, y1: -10, x2: 155, y2: -45 },
    ];

    ctx.fillStyle = '#1a2a3a';
    continents.forEach(cont => {
      const p1 = latLonToXY(cont.y1, cont.x1, width, height);
      const p2 = latLonToXY(cont.y2, cont.x2, width, height);
      ctx.beginPath();
      ctx.roundRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y, 10);
      ctx.fill();
    });
  };

  // 곡선 링크 그리기 (돈 흐름)
  const drawLink = (ctx, sourceNode, targetNode, link, time, width, height) => {
    const source = latLonToXY(sourceNode.lat, sourceNode.lon, width, height);
    const target = latLonToXY(targetNode.lat, targetNode.lon, width, height);

    // 베지어 곡선 컨트롤 포인트
    const midX = (source.x + target.x) / 2;
    const midY = (source.y + target.y) / 2 - 50;

    // 링크 두께 (돈 크기 비례)
    const lineWidth = Math.max(1, Math.sqrt(link.value) / 1000);

    // 그라데이션
    const gradient = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
    if (link.type === 'synergy') {
      gradient.addColorStop(0, 'rgba(0, 255, 136, 0.3)');
      gradient.addColorStop(1, 'rgba(0, 204, 255, 0.3)');
    } else if (link.type === 'investment') {
      gradient.addColorStop(0, 'rgba(255, 51, 102, 0.3)');
      gradient.addColorStop(1, 'rgba(255, 102, 0, 0.3)');
    } else {
      gradient.addColorStop(0, 'rgba(153, 102, 255, 0.3)');
      gradient.addColorStop(1, 'rgba(51, 204, 204, 0.3)');
    }

    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.quadraticCurveTo(midX, midY, target.x, target.y);
    ctx.stroke();

    // 흐르는 파티클 (돈 이동 애니메이션)
    const numParticles = Math.min(5, Math.floor(link.value / 5000000));
    for (let i = 0; i < numParticles; i++) {
      const t = ((time / 2000) + i / numParticles) % 1;
      const px = Math.pow(1-t, 2) * source.x + 2 * (1-t) * t * midX + Math.pow(t, 2) * target.x;
      const py = Math.pow(1-t, 2) * source.y + 2 * (1-t) * t * midY + Math.pow(t, 2) * target.y;

      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = link.type === 'synergy' ? '#00ff88' : link.type === 'investment' ? '#ff3366' : '#9966ff';
      ctx.fill();

      // 글로우 효과
      ctx.beginPath();
      ctx.arc(px, py, 8, 0, Math.PI * 2);
      const glowGradient = ctx.createRadialGradient(px, py, 0, px, py, 8);
      glowGradient.addColorStop(0, link.type === 'synergy' ? 'rgba(0, 255, 136, 0.5)' : 'rgba(255, 51, 102, 0.5)');
      glowGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = glowGradient;
      ctx.fill();
    }
  };

  // 노드 그리기
  const drawNode = (ctx, node, time, width, height, isHovered, isSelected) => {
    const pos = latLonToXY(node.lat, node.lon, width, height);
    const baseRadius = Math.sqrt(node.value) / 5000;
    const radius = baseRadius * (isHovered ? 1.3 : 1) + Math.sin(time / 500 + node.value) * 2;

    // 글로우 효과
    const glowRadius = radius * 2;
    const glow = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, glowRadius);
    glow.addColorStop(0, node.color + '40');
    glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, glowRadius, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();

    // 노드 본체
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    const nodeGradient = ctx.createRadialGradient(pos.x - radius/3, pos.y - radius/3, 0, pos.x, pos.y, radius);
    nodeGradient.addColorStop(0, '#ffffff');
    nodeGradient.addColorStop(0.3, node.color);
    nodeGradient.addColorStop(1, node.color + '88');
    ctx.fillStyle = nodeGradient;
    ctx.fill();

    // 선택 시 링
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius + 5, 0, Math.PI * 2);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // 레이블
    ctx.font = isHovered ? 'bold 14px Arial' : '11px Arial';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText(node.id, pos.x, pos.y + radius + 15);

    if (isHovered) {
      ctx.font = '10px Arial';
      ctx.fillStyle = '#aaaaaa';
      ctx.fillText(node.role, pos.x, pos.y + radius + 28);
    }

    return { x: pos.x, y: pos.y, radius };
  };

  // 메인 렌더링
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    const animate = () => {
      timeRef.current += 16;
      
      ctx.save();
      ctx.translate(offset.x, offset.y);
      ctx.scale(zoom, zoom);

      // 배경
      drawWorldMap(ctx, width, height);

      // 링크 그리기
      links.forEach(link => {
        const sourceNode = nodes.find(n => n.id === link.source);
        const targetNode = nodes.find(n => n.id === link.target);
        if (sourceNode && targetNode) {
          drawLink(ctx, sourceNode, targetNode, link, timeRef.current, width, height);
        }
      });

      // 노드 그리기
      nodes.forEach(node => {
        const isHovered = hoveredNode === node.id;
        const isSelected = selectedNode === node.id;
        drawNode(ctx, node, timeRef.current, width, height, isHovered, isSelected);
      });

      ctx.restore();

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [hoveredNode, selectedNode, zoom, offset]);

  // 마우스 이벤트
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - offset.x) / zoom;
    const y = (e.clientY - rect.top - offset.y) / zoom;

    // 노드 호버 감지
    let found = null;
    for (const node of nodes) {
      const pos = latLonToXY(node.lat, node.lon, canvas.width, canvas.height);
      const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2));
      if (dist < 30) {
        found = node.id;
        break;
      }
    }
    setHoveredNode(found);

    // 드래그
    if (isDragging) {
      setOffset({
        x: offset.x + (e.clientX - dragStart.x),
        y: offset.y + (e.clientY - dragStart.y)
      });
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleClick = () => {
    if (hoveredNode) {
      setSelectedNode(hoveredNode === selectedNode ? null : hoveredNode);
    }
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const newZoom = Math.max(0.5, Math.min(3, zoom - e.deltaY * 0.001));
    setZoom(newZoom);
  };

  const formatMoney = (value) => {
    if (value >= 100000000) return `₩${(value / 100000000).toFixed(1)}억`;
    if (value >= 10000) return `₩${(value / 10000).toFixed(0)}만`;
    return `₩${value.toLocaleString()}`;
  };

  const totalValue = nodes.reduce((sum, n) => sum + n.value, 0);
  const totalSynergy = links.filter(l => l.type === 'synergy').reduce((sum, l) => sum + l.value, 0);

  return (
    <div className="w-full h-screen bg-gray-900 flex flex-col">
      {/* 헤더 */}
      <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🌌</span>
          <div>
            <h1 className="text-white font-bold text-lg">AUTUS Physics Map</h1>
            <p className="text-gray-400 text-xs">Global Money Flow Visualization</p>
          </div>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-gray-400 text-xs">Total Value</div>
            <div className="text-green-400 font-bold">{formatMoney(totalValue)}</div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-xs">Synergy</div>
            <div className="text-cyan-400 font-bold">{formatMoney(totalSynergy)}</div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-xs">Nodes</div>
            <div className="text-white font-bold">{nodes.length}</div>
          </div>
        </div>
      </div>

      {/* 캔버스 */}
      <div className="flex-1 relative">
        <canvas
          ref={canvasRef}
          width={1200}
          height={600}
          className="w-full h-full cursor-grab active:cursor-grabbing"
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleClick}
          onWheel={handleWheel}
        />

        {/* 선택된 노드 정보 */}
        {selectedNode && (
          <div className="absolute top-4 left-4 bg-gray-800 rounded-lg p-4 border border-gray-600 shadow-lg min-w-64">
            <div className="flex items-center gap-3 mb-3">
              <div 
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: nodes.find(n => n.id === selectedNode)?.color }}
              />
              <div>
                <div className="text-white font-bold">{selectedNode}</div>
                <div className="text-gray-400 text-sm">{nodes.find(n => n.id === selectedNode)?.role}</div>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Total Value</span>
                <span className="text-green-400 font-bold">
                  {formatMoney(nodes.find(n => n.id === selectedNode)?.value || 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Connections</span>
                <span className="text-cyan-400">
                  {links.filter(l => l.source === selectedNode || l.target === selectedNode).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Synergy Flow</span>
                <span className="text-yellow-400">
                  {formatMoney(
                    links
                      .filter(l => l.source === selectedNode || l.target === selectedNode)
                      .reduce((sum, l) => sum + l.value, 0)
                  )}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 범례 */}
        <div className="absolute bottom-4 left-4 bg-gray-800 rounded-lg p-3 border border-gray-600">
          <div className="text-gray-400 text-xs mb-2">Flow Types</div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 bg-green-400 rounded" />
              <span className="text-gray-300">Synergy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 bg-pink-500 rounded" />
              <span className="text-gray-300">Investment</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 bg-purple-400 rounded" />
              <span className="text-gray-300">Supply</span>
            </div>
          </div>
        </div>

        {/* 줌 컨트롤 */}
        <div className="absolute bottom-4 right-4 bg-gray-800 rounded-lg p-2 border border-gray-600 flex flex-col gap-1">
          <button 
            onClick={() => setZoom(Math.min(3, zoom + 0.2))}
            className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded text-white text-lg"
          >
            +
          </button>
          <div className="text-center text-gray-400 text-xs py-1">{Math.round(zoom * 100)}%</div>
          <button 
            onClick={() => setZoom(Math.max(0.5, zoom - 0.2))}
            className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded text-white text-lg"
          >
            -
          </button>
          <button 
            onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }}
            className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded text-white text-xs mt-2"
          >
            ↺
          </button>
        </div>

        {/* 수식 표시 */}
        <div className="absolute top-4 right-4 bg-gray-800/90 rounded-lg p-3 border border-gray-600 text-xs">
          <div className="text-gray-400 mb-2">Physics Formula</div>
          <div className="text-cyan-300 font-mono">V = D - T + S</div>
          <div className="text-gray-500 mt-1">
            <div>D: Direct Money</div>
            <div>T: Time Cost</div>
            <div>S: Synergy = k(N₁×N₂)/d²</div>
          </div>
        </div>
      </div>

      {/* 푸터 */}
      <div className="bg-gray-800 px-4 py-2 flex justify-between text-xs text-gray-500 border-t border-gray-700">
        <span>🖱️ Drag to pan | Scroll to zoom | Click node for details</span>
        <span>AUTUS Physics Map v3.0</span>
      </div>
    </div>
  );
};

export default PhysicsMapGlobal;
