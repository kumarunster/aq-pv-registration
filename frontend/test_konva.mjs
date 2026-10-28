import Konva from 'konva';

const stage = new Konva.Stage({ container: 'x', width: 500, height: 500 });
const layer = new Konva.Layer({});
stage.add(layer);

// Group (Element) - wie im Vue-Template
const group = new Konva.Group({ name: 'el-test', x: 100, y: 80 });
// Rect im Inneren - wie im Vue-Template
const rect = new Konva.Rect({ x: 10, y: 20, width: 100, height: 50 });
group.add(rect);
layer.add(group);

// Simuliere Drag: Konva ändert group.x/y
group.x(150); group.y(120);

console.log('group.x:', group.x(), 'rect.x:', rect.x());
console.log('sum (node.x + rect.x):', group.x() + rect.x(), group.y() + rect.y());
console.log('group.getAbsolutePosition():', group.getAbsolutePosition());
console.log('rect.getAbsolutePosition():', rect.getAbsolutePosition());
