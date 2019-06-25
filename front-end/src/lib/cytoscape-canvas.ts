export interface CytoscapeCanvasInstance {
  getCanvas(): HTMLCanvasElement;
  clear(ctx: CanvasRenderingContext2D): void;
  resetTransform(ctx: CanvasRenderingContext2D): void;
  setTransform(ctx: CanvasRenderingContext2D): void;
  drawGrid(ctx: CanvasRenderingContext2D): void;
}

const register = function(cytoscape: (extensionName: string, foo: string, bar: any) => cytoscape.Core) {
  if (!cytoscape) {
    return;
  }

  function cyCanvas(args: Object): CytoscapeCanvasInstance {
    // @ts-ignore
    const cy = this;
    const container = cy.container();

    const canvas = document.createElement('canvas');

    container.appendChild(canvas);

    const defaults = {
      zIndex: 1,
      pixelRatio: 'auto'
    };

    const options = Object.assign({}, defaults, args);

    const pixelRatio: number =
      typeof options.pixelRatio === 'string' ? window.devicePixelRatio || 1 : options.pixelRatio;

    function resize() {
      const width = container.offsetWidth;
      const height = container.offsetHeight;

      const canvasWidth = width * pixelRatio;
      const canvasHeight = height * pixelRatio;

      canvas.width = canvasWidth;
      canvas.height = canvasHeight;

      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      cy.trigger('cyCanvas.resize');
    }

    cy.on('resize', () => {
      resize();
    });

    canvas.setAttribute('style', `position:absolute; top:0; left:0; z-index:${options.zIndex};`);

    resize();

    return {
      /**
       * @return {Canvas} The generated canvas
       */
      getCanvas() {
        return canvas;
      },
      /**
       * Helper: Clear the canvas
       * @param {CanvasRenderingContext2D} ctx
       */
      clear(ctx: CanvasRenderingContext2D) {
        const width = cy.width();
        const height = cy.height();
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, width * pixelRatio, height * pixelRatio);
        ctx.restore();
      },
      /**
       * Helper: Reset the context transform to an identity matrix
       * @param {CanvasRenderingContext2D} ctx
       */
      resetTransform(ctx: CanvasRenderingContext2D) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
      },
      /**
       * Helper: Set the context transform to match Cystoscape's zoom & pan
       * @param {CanvasRenderingContext2D} ctx
       */
      setTransform(ctx: CanvasRenderingContext2D) {
        const pan = cy.pan();
        const zoom = cy.zoom();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.translate(pan.x * pixelRatio, pan.y * pixelRatio);
        ctx.scale(zoom * pixelRatio, zoom * pixelRatio);
      },
      drawGrid(ctx: CanvasRenderingContext2D) {
        const pan = cy.pan();
        const width = cy.width();
        const height = cy.height();
        const zoom = cy.zoom() * pixelRatio;

        const panX = pan.x * pixelRatio;
        const panY = pan.y * pixelRatio;

        const xStart = Math.floor(-panX / zoom / 100) * 100;
        const yStart = Math.floor(-panY / zoom / 100) * 100;

        const xEnd = xStart + Math.floor((width / zoom + 300) / 100) * 100;
        const yEnd = yStart + Math.floor((height / zoom + 300) / 100) * 100;

        ctx.beginPath();
        ctx.strokeStyle = '#d0cad0';
        ctx.lineWidth = 1.1;
        for (let y = yStart; y < yEnd; y += 100) {
          ctx.moveTo(xStart, y);
          ctx.lineTo(xEnd, y);
        }

        for (let x = xStart; x < xEnd; x += 100) {
          ctx.moveTo(x, yStart);
          ctx.lineTo(x, yEnd);
        }
        ctx.stroke();

        ctx.lineWidth = 0.7;
        for (let y = yStart; y < yEnd; y += 25) {
          if (y % 100 === 0) {
            continue;
          }
          ctx.moveTo(xStart, y);
          ctx.lineTo(xEnd, y);
        }

        for (let x = xStart; x < xEnd; x += 25) {
          if (x % 100 === 0) {
            continue;
          }
          ctx.moveTo(x, yStart);
          ctx.lineTo(x, yEnd);
        }
        ctx.stroke();
      }
    };
  }

  cytoscape('core', 'cyCanvas', cyCanvas);
};

export default function registerExtension(cytoscape: (extensionName: string, foo: string, bar: any) => cytoscape.Core) {
  register(cytoscape);
}
