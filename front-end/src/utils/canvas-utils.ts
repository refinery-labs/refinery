export function drawImageGrid(
  cy: cytoscape.Core,
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  repeatX: number,
  repeatY: number,
  ratio: number = 4
) {
  for (let y = -repeatY; y < repeatY; y++) {
    for (let x = -repeatX; x < repeatX; x++) {
      ctx.drawImage(
        image,
        (x * image.width) / ratio,
        (y * image.width) / ratio,
        image.width / ratio,
        image.height / ratio
      );
    }
  }
}
