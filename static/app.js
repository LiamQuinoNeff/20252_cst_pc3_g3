(function(){
  const canvas = document.getElementById('world');
  const ctx = canvas.getContext('2d');
  let space = {w:30,h:30};
  function clear(){ ctx.clearRect(0,0,canvas.width,canvas.height); }
  function draw(data){
    const fishes = data.fishes || [];
    clear();
    // scale world to canvas
    const pad = 10;
    const W = canvas.width - pad*2;
    const H = canvas.height - pad*2;
    const sx = W / (space.w || 1);
    const sy = H / (space.h || 1);
    // draw recent removals as flashes
    const removals = data.removals || [];
    const now = Date.now() / 1000;
    for(const r of removals){
      if(!r.x || !r.y) continue;
      const elapsed = now - (r.time || 0);
      if(elapsed < 1.2){
        const alpha = Math.max(0, 1 - (elapsed / 1.2));
        const rx = pad + (r.x||0)*sx;
        const ry = pad + (r.y||0)*sy;
        ctx.beginPath();
        ctx.globalAlpha = alpha * 0.9;
        ctx.fillStyle = '#ff4444';
        ctx.arc(rx, ry, 12 * (1 - elapsed / 1.2) + 6, 0, Math.PI*2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }
    }
    for(const f of fishes){
      const x = pad + (f.x||0)*sx;
      const y = pad + (f.y||0)*sy;
      // determine radius from size (fallback to constant) — visually scaled
      const sizeVal = (typeof f.size === 'number') ? Math.max(0.4, f.size) : 1.0;
      const radius = Math.round(4 + sizeVal * 6);
      // color: reproducers (foods>=2) -> red, ate once -> blue, else grey
      let fill = '#777777';
      if((f.foods_eaten||0) >= 2) fill = '#cc2222';
      else if((f.foods_eaten||0) === 1) fill = '#0066cc';
      else fill = '#444444';
      ctx.beginPath();
      ctx.fillStyle = fill;
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1.5;
      ctx.arc(x, y, radius, 0, Math.PI*2);
      ctx.fill();
      ctx.stroke();
      // draw small inner dot for sense (visual cue)
      if(typeof f.sense === 'number'){
        const inner = Math.max(1, Math.round(f.sense));
        ctx.beginPath();
        ctx.fillStyle = '#ffffff';
        ctx.arc(x + radius - inner - 1, y - radius + inner + 1, inner, 0, Math.PI*2);
        ctx.fill();
      }
      // draw label (short jid)
      try{
        const short = (f.jid || '').split('@')[0];
        ctx.fillStyle = '#111';
        ctx.font = '10px Arial';
        ctx.fillText(short, x + radius + 4, y + 3);
      }catch(e){}
    }
    // draw foods (small green dots)
    if(data.foods && data.foods.length){
      for(const food of data.foods){
        const fx = pad + (food[0]||0)*sx;
        const fy = pad + (food[1]||0)*sy;
        ctx.beginPath();
        ctx.fillStyle = '#2e8b57';
        ctx.strokeStyle = '#1f5f3f';
        ctx.lineWidth = 1;
        ctx.arc(fx, fy, 4, 0, Math.PI*2);
        ctx.fill();
        ctx.stroke();
      }
    }
  }
  async function poll(){
    try{
      const res = await fetch('/fishes');
      if(!res.ok) return;
      const data = await res.json();
      if(data.space_size){ space.w = data.space_size[0]; space.h = data.space_size[1]; }
      draw(data);
    }catch(e){ console.error(e); }
  }
  // poll loop
  setInterval(poll, 250);
  // initial
  poll();
})();