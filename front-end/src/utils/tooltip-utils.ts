const tooltipStyle = `
<style>
  * {
    font-size: .875rem;
  }
  .btn {
    background: transparent;
    border: .05rem solid #fff;
    border-radius: .1rem;
    color: #fff;
    cursor: pointer;
    display: inline-block;
    outline: none;
    margin: 0 .2rem;
    padding: .35rem;
    text-align: center;
    text-decoration: none;
    -webkit-transition: all .2s ease;
    transition: all .2s ease;
    vertical-align: middle;
    white-space: nowrap;
    font-size: .6rem;
  }
  .step {
    color: white;
    background: #50596c;
    max-width: 320px;
    border-radius: 3px;
    -webkit-filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.5));
    filter: drop-shadow(0 0 2px rgba(0, 0, 0, 0.5));
    padding: 1rem;
    text-align: center;
  }
  .header {
    margin: -1rem -1rem .5rem;
    padding: .5rem;
    background-color: #454d5d;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
  }
  .content {
    font-size: .7rem;
    margin-bottom: .5rem;
  }
</style>
`;

export function generateTooltipSVGContents(header: string, body: string): string {
  return `
  <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
    <foreignObject width="100%" height="100%">
      <div xmlns="http://www.w3.org/1999/xhtml" style="">
        ${tooltipStyle}
        <div class="step">
          <div class="header">
            ${header}
          </div>
          <div class="content">
            ${body}
          </div>
            <button class="btn">
              continue
            </button>
        </div>
      </div>
    </foreignObject>
  </svg>`;
}
