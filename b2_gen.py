from pathlib import Path
import json

def scan_folder(path, ignore=['venv', '__pycache__', '.git']):
    if path.name in ignore:
        return None
    
    images = []
    texts = []
    children = []
    
    if path.is_dir():
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name in ignore:
                continue
            if item.is_file():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    images.append(str(item.relative_to('.')))
                elif item.suffix.lower() in ['.txt', '.md']:
                    texts.append(str(item.relative_to('.')))
            elif item.is_dir():
                child = scan_folder(item, ignore)
                if child:
                    children.append(child)
        
        all_images = images.copy()
        all_texts = texts.copy()
        for child in children:
            all_images.extend(child['all_images'])
            all_texts.extend(child['all_texts'])
    
    content_type = 'empty'
    if all_images and all_texts:
        content_type = 'mixed'
    elif all_images:
        content_type = 'images'
    elif all_texts:
        content_type = 'text'
    
    return {
        'name': path.name,
        'path': str(path.relative_to('.')),
        'type': content_type,
        'children': children,
        'all_images': all_images,
        'all_texts': all_texts,
        'own_images': images,
        'own_texts': texts
    }

root = scan_folder(Path('.'))

with open('data.json', 'w') as f:
    json.dump(root, f, indent=2)

with open('index.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html>
<head>

<script src="https://unpkg.com/stats.js@0.17.0/build/stats.min.js"></script>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    background: black; 
    color: white; 
    font-family: monospace; 
    font-size: 11px;
    display: flex;
    height: 100vh;
    overflow: hidden;
}
#tree { 
    width: 300px; 
    border-right: 1px solid black; 
    overflow-y: auto; 
    padding: 10px;
}
#content { 
    flex: 1; 
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
}
.tree-item { white-space: pre; }
.tree-link { cursor: pointer; color: #4af; }
.tree-link:hover { background: #222; }
.content-div {
    border: 1px solid black;
    position: relative;
    overflow: hidden;
}
.div-label {
    position: absolute;
    top: 5px;
    left: 5px;
    background: black;
    padding: 2px 5px;
    border: 1px solid black;
    z-index: 100;
}
.text-content {
    padding: 20px;
    overflow-y: auto;
    white-space: pre-wrap;
}
canvas { display: block; width: 100%; height: 100%; }
</style>
</head>
<body>
<div id="tree"></div>
<div id="content"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
let data;
let activeScenes = [];

fetch('data.json')
    .then(r => r.json())
    .then(d => {
        data = d;
        buildTree(data, document.getElementById('tree'));
    });

function buildTree(node, container, depth = 0, isLast = true, prefix = '') {
    const connector = isLast ? '└── ' : '├── ';
    
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    
    const link = document.createElement('span');
    link.className = 'tree-link';
    link.textContent = node.name;
    link.onclick = (e) => {
        e.stopPropagation();
        renderContent(node);
    };
    
    item.appendChild(link);
    container.appendChild(item);
    
    const newPrefix = prefix + (isLast ? '    ' : '│   ');
    node.children.forEach((child, i) => {
        buildTree(child, container, depth + 1, i === node.children.length - 1, newPrefix);
    });
}

class OrbitControls {
 constructor(camera, domElement) {
        this.camera = camera;
        this.domElement = domElement;
        this.target = new THREE.Vector3();
        this.theta = Math.PI / 4;
        this.phi = Math.PI / 4;
        this.zoom = 1;
        this.isDragging = false;
        this.isPanning = false;
        this.lastMouse = { x: 0, y: 0 };
        
        this.domElement.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.domElement.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.domElement.addEventListener('mouseup', this.onMouseUp.bind(this));
        this.domElement.addEventListener('wheel', this.onWheel.bind(this));
        this.update();
    }
    
        
onMouseDown(e) {
    if (e.button === 0) this.isDragging = true;
    if (e.button === 1) this.isPanning = true;
    this.lastMouse = { x: e.clientX, y: e.clientY };
    e.preventDefault();
}

    onMouseMove(e) {
        const dx = e.clientX - this.lastMouse.x;
        const dy = e.clientY - this.lastMouse.y;
        
        if (this.isDragging) {
            this.theta -= dx * 0.005;
            this.phi -= dy * 0.005;
            this.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.phi));
            this.update();
        }
        
        if (this.isPanning) {
            const panSpeed = 0.01 / this.zoom;
            this.target.x -= dx * panSpeed;
            this.target.y += dy * panSpeed;
            this.update();
        }
        
        this.lastMouse = { x: e.clientX, y: e.clientY };
    }
    
    onMouseUp() {
        this.isDragging = false;
        this.isPanning = false;
    }
    
    onWheel(e) {
        e.preventDefault();
        this.zoom *= (e.deltaY > 0 ? 1.1 : 0.9);
        this.zoom = Math.max(0.1, Math.min(10, this.zoom));
        this.camera.zoom = this.zoom;
        this.camera.updateProjectionMatrix();
    }
    
    update() {
        const radius = 20;
        const x = radius * Math.sin(this.phi) * Math.sin(this.theta);
        const y = radius * Math.cos(this.phi);
        const z = radius * Math.sin(this.phi) * Math.cos(this.theta);
        
        this.camera.position.set(x + this.target.x, y + this.target.y, z + this.target.z);
        this.camera.lookAt(this.target);
    }

}

function disposeScene(sceneData) {
    if (sceneData.animationId) cancelAnimationFrame(sceneData.animationId);
    if (sceneData.renderer) {
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }
    }
    if (sceneData.scene) {
        sceneData.scene.traverse(obj => {
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) {
                if (obj.material.map) obj.material.map.dispose();
                obj.material.dispose();
            }
        });
    }
}



function createThreeScene(container, images) {

 const scene = new THREE.Scene();
    const frustumSize = 10;
    const aspectRatio = container.clientWidth / container.clientHeight;
    const camera = new THREE.OrthographicCamera(
        frustumSize * aspectRatio / -2,
        frustumSize * aspectRatio / 2,
        frustumSize / 2,
        frustumSize / -2,
        0.1,
        1000
    );
    camera.position.set(10, 10, 10);
    
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    
    const controls = new OrbitControls(camera, renderer.domElement);
    
    const grouped = {};
    images.forEach(imgPath => {
        const parts = imgPath.split('/');
        const folder = parts.length > 1 ? parts[parts.length - 2] : 'root';
        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgPath);
    });
    
    const folders = Object.keys(grouped);
    const cols = Math.ceil(Math.sqrt(folders.length));
    const spacing = 3;
    
    folders.forEach((folder, stackIdx) => {
        const stackImages = grouped[folder];
const row = Math.floor(stackIdx / cols);
const col = stackIdx % cols;
const xPos = (col - cols / 2) * spacing;
const zPos = (row - Math.ceil(folders.length / cols) / 2) * spacing;

stackImages.forEach((imgPath, i) => {
    const loader = new THREE.TextureLoader();
    loader.load(imgPath, (texture) => {
        texture.minFilter = THREE.NearestFilter;
        texture.magFilter = THREE.NearestFilter;
        
        const aspect = texture.image.width / texture.image.height;
        const height = 1.5;
        const width = height * aspect;
        
        const geometry = new THREE.PlaneGeometry(width, height);
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 1
        });
        const mesh = new THREE.Mesh(geometry, material);
        
        mesh.position.x = xPos;
        mesh.position.y = i * 0.1;
        mesh.position.z = zPos;
        mesh.rotation.x = Math.PI / 2;
        mesh.rotation.y = Math.PI;
        mesh.rotation.z = Math.PI;
        
        scene.add(mesh);
        
        const edges = new THREE.EdgesGeometry(geometry);
        const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }));
        line.position.set(mesh.position.x, mesh.position.y, mesh.position.z);
        line.rotation.copy(mesh.rotation);
        scene.add(line);
    });
});       

    });
    

const stats = new Stats();
stats.showPanel(0);
container.appendChild(stats.dom);
stats.dom.style.position = 'absolute';
stats.dom.style.top = '30px';
stats.dom.style.left = '5px';

const sceneData = { scene, renderer, camera, controls, animationId: null };

function animate() {
    stats.begin();
    sceneData.animationId = requestAnimationFrame(animate);
    controls.update();
    scene.rotation.y += 0.001;
    renderer.render(scene, camera);
    stats.end();
}
animate();






    
    activeScenes.push(sceneData);
    
    window.addEventListener('resize', () => {
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });


}


async function loadText(path) {
    const res = await fetch(path);
    return await res.text();
}


async function renderContent(node) {
    activeScenes.forEach(disposeScene);
    activeScenes = [];
    
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
    
    const children = node.children.length > 0 ? node.children : [node];
    const count = children.length;
    const cols = Math.ceil(Math.sqrt(count));
    
    for (const child of children) {
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.width = `calc(${100/cols}% - 2px)`;
        div.style.height = count <= 2 ? '100%' : `calc(${100/Math.ceil(count/cols)}% - 2px)`;
        
        const label = document.createElement('div');
        label.className = 'div-label';
        label.textContent = child.name;
        div.appendChild(label);
        
        if (child.all_images.length > 0 && child.all_texts.length > 0) {
            div.style.display = 'flex';
            div.style.flexDirection = 'column';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.flex = '1';
            let textContent = '';
            for (const path of child.all_texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            textDiv.appendChild(pre);
            div.appendChild(textDiv);
            
            const imgDiv = document.createElement('div');
            imgDiv.style.flex = '1';
            imgDiv.style.position = 'relative';
            div.appendChild(imgDiv);
            setTimeout(() => createThreeScene(imgDiv, child.all_images), 0);
        } else if (child.all_images.length > 0) {
            setTimeout(() => createThreeScene(div, child.all_images), 0);
        } else if (child.all_texts.length > 0) {
            div.className = 'content-div text-content';
            let textContent = '';
            for (const path of child.all_texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            pre.style.marginTop = '30px';
            div.appendChild(pre);
        }
        
        contentDiv.appendChild(div);
    }
}

</script>
</body>
</html>''')

print("Generated data.json and index.html")
