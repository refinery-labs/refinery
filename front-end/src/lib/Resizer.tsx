import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';

@Component
export default class Resizer extends Vue {
  dragging = false;

  lastX = 0;
  lastY = 0;

  @Prop({ required: true }) onSizeChanged!: (deltaX: number, deltaY: number) => void;

  mounted() {
    const body = document.querySelector('body');

    if (!body) {
      return;
    }

    body.addEventListener('mousemove', this.onMouseMove);

    body.addEventListener('mouseup', this.onMouseUp);
  }

  onMouseUp(e: MouseEvent) {
    if (!this.dragging) {
      return;
    }

    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;
  }

  onMouseMove(e: MouseEvent) {
    if (!this.dragging) {
      return;
    }

    const deltaX = e.x - this.lastX;
    const deltaY = e.y - this.lastY;

    this.lastX = e.x;
    this.lastY = e.y;

    this.onSizeChanged(deltaX, deltaY);
  }

  onMouseDown(e: MouseEvent) {
    e.preventDefault();
    if (!this.dragging) {
      this.lastX = e.x;
      this.lastY = e.y;
      this.dragging = true;
    }
  }

  render() {
    return <div class="show-block-container__resizer" on={{ mousedown: this.onMouseDown }} />;
  }
}
