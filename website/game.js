(() => {
  const canvas = document.getElementById('game');
  const ctx = canvas.getContext('2d');
  const scoreEl = document.getElementById('score');
  const restartBtn = document.getElementById('restart');

  const gridSize = 20; // how many cells per row/col
  const cell = canvas.width / gridSize; // pixel size of each cell

  let snake = [{ x: 10, y: 10 }];
  let dir = { x: 1, y: 0 };
  let nextDir = { x: 1, y: 0 };
  let food = null;
  let running = true;
  let speed = 8; // frames per second
  let score = 0;

  function randCell() {
    return {
      x: Math.floor(Math.random() * gridSize),
      y: Math.floor(Math.random() * gridSize)
    };
  }

  function placeFood() {
    let p = randCell();
    // avoid placing on snake
    while (snake.some(s => s.x === p.x && s.y === p.y)) p = randCell();
    food = p;
  }

  function reset() {
    snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
    dir = { x: 1, y: 0 };
    nextDir = { x: 1, y: 0 };
    score = 0;
    scoreEl.textContent = score;
    running = true;
    placeFood();
  }

  function update() {
    // apply queued direction but prevent reversing
    if (!(nextDir.x === -dir.x && nextDir.y === -dir.y)) {
      dir = nextDir;
    }

    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };

    // wall collision
    if (head.x < 0 || head.x >= gridSize || head.y < 0 || head.y >= gridSize) {
      running = false;
      return;
    }

    // self collision
    if (snake.some(s => s.x === head.x && s.y === head.y)) {
      running = false;
      return;
    }

    snake.unshift(head);

    // eating
    if (food && head.x === food.x && head.y === food.y) {
      score += 1;
      scoreEl.textContent = score;
      placeFood();
    } else {
      snake.pop();
    }
  }

  function draw() {
    // clear
    ctx.fillStyle = '#0b0b0f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // draw snake
    ctx.fillStyle = '#00f7ff';
    snake.forEach((s, i) => {
      ctx.fillStyle = i === 0 ? '#ff004d' : '#00f7ff'; // head red, body cyan
      ctx.fillRect(s.x * cell, s.y * cell, cell - 2, cell - 2);
    });

    // draw food
    if (food) {
      ctx.fillStyle = '#fff200';
      ctx.fillRect(food.x * cell, food.y * cell, cell - 2, cell - 2);
    }

    // game over text
    if (!running) {
      ctx.fillStyle = '#ff004d';
      ctx.font = "20px Orbitron, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("GAME OVER - Press Restart", canvas.width / 2, canvas.height / 2);
    }
  }

  // keyboard control
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowUp') nextDir = { x: 0, y: -1 };
    if (e.key === 'ArrowDown') nextDir = { x: 0, y: 1 };
    if (e.key === 'ArrowLeft') nextDir = { x: -1, y: 0 };
    if (e.key === 'ArrowRight') nextDir = { x: 1, y: 0 };
  });

  // restart button
  restartBtn.addEventListener('click', () => {
    reset();
  });

  // main loop
  function loop() {
    if (running) update();
    draw();
    setTimeout(loop, 1000 / speed);
  }

  reset();
  loop();
})();
