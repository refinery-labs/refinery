import {CreateElement, VNode} from 'vue';
import {Component, Vue} from 'vue-property-decorator';
import {Layer} from 'konva/types/Layer';
import {Shape, ShapeConfig} from 'konva/types/Shape';
import Konva from 'konva';
import {Stage} from 'konva/types/Stage';

export declare type KonvaLayer = {
  getNode: () => Layer,
  getStage: () => Stage
};

@Component
export default class RefineryGraph extends Vue {
  shapes: ShapeConfig[] = [];
  
  public getStage() {
    if (!this.$refs.stage) {
      return null;
    }
    
    const rawStage = this.$refs.stage as unknown;
    return (rawStage as KonvaLayer).getStage();
  }
  
  public handleDragstart(e: Event) {
    const rawShape = e.target as unknown;
    const rawDragLayer = this.$refs.dragLayer as unknown;
    const rawStage = this.$refs.stage as unknown;
  
    const shape = rawShape as Shape;
    const dragLayer = (rawDragLayer as KonvaLayer).getNode();
    const stage = (rawStage as KonvaLayer).getNode();
    
    // moving to another layer will improve dragging performance
    shape.moveTo(dragLayer);
    stage.draw();
    shape.setAttrs({
      shadowOffsetX: 15,
      shadowOffsetY: 15,
      scaleX: shape.getAttr("startScale") * 1.2,
      scaleY: shape.getAttr("startScale") * 1.2
    });
  }
  
  public handleDragend(e: Event) {
    const rawShape = e.target as unknown;
    const rawLayer = this.$refs.layer as unknown;
    const rawStage = this.$refs.stage as unknown;
    
    const shape = rawShape as Shape;
    const layer = (rawLayer as KonvaLayer).getNode();
    const stage = (rawStage as KonvaLayer).getNode();
    
    shape.moveTo(layer);
    stage.draw();
    shape.to({
      duration: 0.5,
      easing: Konva.Easings.ElasticEaseOut,
      scaleX: shape.getAttr("startScale"),
      scaleY: shape.getAttr("startScale"),
      shadowOffsetX: 5,
      shadowOffsetY: 5
    });
  }
  
  public mounted() {
    const stage = this.getStage();
    
    if (!stage) {
      return;
    }
  
    for (let n = 0; n < 30; n++) {
      const scale = Math.random();
      this.shapes.push({
        x: Math.random() * stage.width(),
        y: Math.random() * stage.height(),
        rotation: Math.random() * 180,
        numPoints: 5,
        innerRadius: 30,
        outerRadius: 50,
        fill: "#89b717",
        opacity: 0.8,
        draggable: true,
        scaleX: scale,
        scaleY: scale,
        shadowColor: "black",
        shadowBlur: 10,
        shadowOffsetX: 5,
        shadowOffsetY: 5,
        shadowOpacity: 0.6,
        startScale: scale
      });
    }
  }
  
  public renderStar(config: ShapeConfig) {
    return (
      <v-star key={config.id} config={config} />
    );
  }
  
  public render(h: CreateElement): VNode {
    const config = {
      configKonva: {
        width: 200,
        height: 200
      }
    };
    
    const eventHandlers = {
      dragstart: (e: Event) => this.handleDragstart(e),
      dragend: (e: Event) => this.handleDragend(e)
    };
    
    return (
      <div class="refinery-graph-container">
        <v-stage
          ref="stage"
          config={config.configKonva}
          on={eventHandlers}>
          <v-layer ref="layer">
            {/*<v-circle config={config.configCircle} />*/}
            {this.shapes.map(config => this.renderStar(config))}
          </v-layer>
          <v-layer ref="dragLayer"></v-layer>
        </v-stage>
      </div>
    );
  }
}
