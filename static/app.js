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
    for(const f of fishes){
      const x = pad + (f.x||0)*sx;
      const y = pad + (f.y||0)*sy;
      // draw circle
      ctx.beginPath();
      ctx.fillStyle = '#0077cc';
      ctx.strokeStyle = '#005fa3';
      ctx.lineWidth = 1;
      ctx.arc(x, y, 6, 0, Math.PI*2);
      ctx.fill();
      ctx.stroke();
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