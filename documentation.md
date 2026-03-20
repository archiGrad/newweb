docs

the whole website runs on the fact that images with transparancy can represnt 3d objects at a lower memory cost (but reduced accuracy) than traditional 3d models.  this allows us to use highly complex models as simple 2d textures instead of loading them in as geometry files.  we can do things with images thatv we cant do with 3d objects.

image comparing, image layering, optimize more efficient by removing duplicates (which they re a lot), postprocessing effects(sharpoen, overlay, dither, animate),  etc


supported extensions.
png, jpg, gif, html

this whole website act as a folderstructure with folders and content inside. files can propagate through these folders. they can ;'bubble up' to the surface. this is the case for both images and text documents


text

text can only be written only in a .html document with template

"

<div class="text_center_fullscreen">
  <div class="home_inner">
    <span>archigrad.io</span> 
<br>is making architecture</span>.
    <br>welcome to our website</span>.
  </div>
</div>




"

with text_center_fullscreen being a possible class
styling happens with inline styles or from the global styles.css file


"

<div class="text_center_fullscreen">
  <div class="home_inner">
    <br><span style="font-size:1em;">archigrad.io</span> 
  </div>
</div>

with style tag you can add custom slyling

"



but also with js additions




""
<div class="text_center_fullscreen">
  <div class="home_inner">
   <span>archigrad.io</span> 
<br>is making architecture</span>] .
  </div>
</div>
<script>
    console.log("hello there")
</script>




""
custom styling can be found in styles.css or can be done inline as shown here

in root are the main ones that define background colors, fontsizes etc. 
"
/* Override these to change font sizes without re-running the Python script */
:root {
    --font-ui: 12px;
    --font-dots-sm: 14px;
    --font-dots-md: 14px;
    --font-page-index: 14px;
    --font-loading-grid: 14px;
    --text-content-fontsize: 16px;
}

"

example html layouts with code

img1
img2
img3
img4
img5



bubbling up

example how this file bubbles up



when a html file is on 
archigrad.io   ----> file will be visible here
	projects
		project_01
			project_01.html

then that file will be visible on all levels bubbling up until archiGrad.io

this behaviour is not always wanted so there are 2 ways of handling it by adding dotfiles that can interject this behaviour

# HTML 
 you can add dotfiles in folders. there are 2 html related dotfiles. .html_only_here and .html_stops_here. you dont have to write anything inside of these files, they just have to be tyhere. they are not mandatorty also. 

### `.html_only_here`

Think of it as: "my HTML stays at this level only."

### `.html_stops_here`

Think of it as: "no HTML passes through this ceiling."

## How to use

Place an empty file with the name in any directory. The file content doesn't matter — only its presence.
easiest way is to just make a new file in a folder and call it .html_stops_here or .html_only_here

-----------------

you can see from tyhe website itself (IMG) where those files are as they are represented by a colored dot. this makes it easy for debugging also. it also shows if html files propagate by colored dotsd. (IMG)

In both the tree view and breadcrumb labels, dots appear next to folder names: (IMG)

- **Blue dot** — `.html_only_here` is present in this folder
- **Green dot** — `.html_stops_here` is present in this folder
- **White dots** (or colored if `COLORED_HTML_DOTS = True`) — each dot represents one HTML file accumulated at this node. The number of dots shows how many HTML files are visible when you click that folder. When `COLORED_HTML_DOTS` is enabled, each H
TML file gets a deterministic random color based on its file path and the `SEED` value, so the same file always appears as the same color across all nodes it propagates through.

## Examples

Legend: `X` = .html_stops_here, `I` = .html_only_here, `O` = white dot (one per accumulated HTML file)

---

Example 1 — No dotfiles (default behavior)
All HTML files propagate to the root.
└── archigrad.io  O O O
    ├── projects  O O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02
    │       └── page.html
    └── about
        └── page.html
Example 2 — .html_only_here on a leaf folder
The leaf's HTML stays at its level, parent doesn't receive it.
└── archigrad.io  O O
    ├── projects  O O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02
    │       └── page.html
    └── about  I
        └── page.html
Example 3 — .html_stops_here on a mid-level folder
Nothing below projects propagates to root.
└── archigrad.io  O
    ├── projects  X  O O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02
    │       └── page.html
    └── about
        └── page.html
Example 4 — .html_only_here on a mid-level folder with children
projects keeps its accumulated content (own + children) but doesn't send it up.
└── archigrad.io  O
    ├── projects  I  O O O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02
    │       ├── page.html
    │       └── credits.html
    └── about
        └── page.html
Example 5 — Multiple .html_only_here at same level
Each sibling is isolated from the parent independently.
└── archigrad.io  (no dots)
    ├── projects  I
    │   └── page.html
    ├── competitions  I
    │   └── page.html
    └── about  I
        └── page.html
Example 6 — .html_stops_here at root level
Nothing propagates at all. Each folder only shows its own subtree when clicked.
└── archigrad.io  X
    ├── projects  O O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02
    │       └── page.html
    └── about  O
        └── page.html
Example 7 — Nested .html_stops_here
Each boundary is independent. project_02 blocks its children from reaching projects, and projects blocks everything from reaching root.
└── archigrad.io  O
    ├── projects  X  O
    │   ├── project_01
    │   │   └── page.html
    │   └── project_02  X  O O
    │       ├── part_01
    │       │   └── page.html
    │       └── part_02
    │           └── page.html
    └── about
        └── page.html
Example 8 — .html_only_here inside a .html_stops_here subtree
project_02 has .html_stops_here so nothing reaches projects. Inside, part_01 has .html_only_here so its HTML doesn't reach project_02 either.
└── archigrad.io  (no dots)
    └── projects  X
        └── project_02  X  O
            ├── part_01  I  O
            │   └── page.html
            └── part_02  O
                └── page.html
Example 9 — Mixed content (HTML + images)
Dotfiles only affect HTML propagation. Images always propagate regardless.
└── archigrad.io  O O  (2 HTML files, images also present but not shown as dots)
    ├── projects  I  O
    │   ├── description.html
    │   └── render_01.jpg         (image propagates normally to root)
    └── about
        └── page.html
---

### Example 9 — Mixed content (HTML + images)

Dotfiles only affect HTML propagation. Images always propagate regardless.

```
└── root  O O  (2 HTML files, images also present but not shown as dots)
    ├── gallery  I  O
    │   ├── description.html
    │   └── photo1.jpg         (image propagates normally to root)
    └── docs
        └── readme.html
```

---

these are examples of website layouts and their code. you can combine them 







3d models


as described before, the website does not load 3d models, only textures

we can slice 3d models and (coming soon combining with a displacement system) recreate a 2d version of that model(slice), stores on a spritesheet.

(IMG)

on this spritesheet, all images are loaded. this is done so we only need to make 1 request to get a spritesheet (containing sometimes hundreds of images). becasue requesting images 1 by 1 takes long time . the spritesheet is also stored as a kx2 file which does not need to be decompressed on the gpu. it saves about 4x memory over a png file.

also gifs are stored on this sheet as multiple frames layed out on this spritesheet



how to add images?


very simple, in archigrad.io folder, make a folder and put images in it. 

what you can do:
put images in folder
put images in folder/folder/folder/image1

what you cant do
put images in a folder that already contains a folder
archigrad.io
    projects
        project_1
            image1
            image2
            image3
        imagea
        imageb
        imagec

how to control

everything is controlled by 2 things
.custom_processing
the default global vars in file.py

.custom_processing - Per-folder override file
Place this file in any folder to override global defaults for that folder and its children.
Uncomment lines to activate. If omitted, the global default from the script is used.



a normal example can be , 
"

SPRITE_SIZE = 256
STACK_SPACING = 0.0787
ZOOM_VALUE = 0.5
GIF_SPEED = 0.775
IMAGE_SETTINGS_CUSTOMTEXT = "hello"
IMAGE_SETTINGS_COLOR = 'green'
# IMAGE_SETTINGS_FONTSIZE = 3
COLOR_TO_TRANSPARENT = 'light_gray'
COLOR_THRESHOLD = 60


# SHARPEN = True
# SHARPEN_RADIUS = 2
# SHARPEN_PERCENT = 100
# SHARPEN_THRESHOLD = 3
# GAUSSIAN_BLUR = False
# GAUSSIAN_BLUR_RADIUS = 2

# DITHERING = True
# DITHER_MODE = 'custom_palette'
# DITHER_METHOD = 'ordered'
# DITHER_COLORS = 256
# CUSTOM_PALETTE = ['#000000', '#FF0000', '#00FF00']
# MAX_GIF_FRAMES = 30
# IMAGE_SETTINGS_LABELS = False
# TEXT_IMAGE_RESOLUTION = 512
# SQUARE_IMAGES = True


"

and they can be set per stack or per folder


the following variables can be set in the python as they dont imply individual control.


SPRITESHEET_SIZE explain 
RESIZE_METHOD explain
LABEL_SPRITE_SIZE explain
LOD_TARGET_SPRITE_SIZES explain
LOD_VIEWHEIGHT_THRESHOLDS explain
STACK_DIM_OPACITY explain
SEED   explain
QUICKLOAD_THRESHOLD explain
ORDERED_GRID_LAYOUT
ROTATION_SPEED
RANDOM_ZOOM
RANDOM_TEXTDIV_POSITION
DIV_RATIO_HALF
LOADINGSCREEN_IMG_INCREMENT
MAX_LABELS
SCREEN_BUFFER
COLORED_HTML_DOTS
BREADCRUMB_HTML_DOTS
SHOW_NAV_ACCESSORIES
SUBMENU_CLOSE_DELAY
WIRE_STRAIGHT


SPRITESHEET_SIZE (4096) — Maximum pixel dimension of each spritesheet. All sprites are packed into sheets of this size. Larger = fewer sheets but bigger files.
RESIZE_METHOD (Image.LANCZOS) — The downscaling algorithm used when resizing images to SPRITE_SIZE. LANCZOS is high-quality. Not user-facing, hardcoded.
LABEL_SPRITE_SIZE (512) — Sprite size specifically for the text label images (folder names) on spritesheets. Separate from SPRITE_SIZE so labels can be sharper than image sprites. Overridden to 128 in low-res mode.
LOD_TARGET_SPRITE_SIZES ([None, 32, 8]) — Level of Detail system. Three tiers: LOD0 uses original resolution (None), LOD1 downscales spritesheets to 32px per sprite, LOD2 to 8px. When zoomed out, the viewer swaps to lower-res sheets to save GPU memory.
LOD_VIEWHEIGHT_THRESHOLDS ([20, 40]) — Controls when the viewer switches between LOD levels. If the camera's view height is below 20, use LOD0 (full detail). Below 40, use LOD1. Above 40, use LOD2 (lowest detail).
STACK_DIM_OPACITY (0.1) — When navigating into a folder, all non-active stacks are dimmed to this opacity (0.0 = invisible, 1.0 = fully visible). Helps focus attention on the selected content.
SEED (2922) — Global seed for all deterministic randomness: colored HTML dots, random zoom values, and random text/image div positioning. Changing this changes all seeded behavior consistently.
QUICKLOAD_THRESHOLD (100) — Defined in defaults and passed to the viewer config, but not currently used in the JS viewer code. Likely reserved for a future loading strategy switch based on image count.
ORDERED_GRID_LAYOUT (True) — When True, stacks are arranged in a grid pattern. When False, stacks would be placed differently (scattered/free-form). The grid dimensions are read from each node's grid_layout property (e.g. "3x2").
ROTATION_SPEED (0.000015) — The entire 3D scene auto-rotates on the Y axis. This controls how fast. Very small values = slow ambient rotation.
RANDOM_ZOOM (False) — When True, each page gets a random zoom level (0.1, 0.4, or 1.0) based on the SEED. When False, uses ZOOM_VALUE for all pages. Per-node zoom (mzm) always overrides both.
RANDOM_TEXTDIV_POSITION (False) — When a content div has both images and HTML text, they sit side by side. When True, the left/right order is randomized per folder (using SEED). When False, text is always on the left, images on the right.
DIV_RATIO_HALF (False) — When False and there are exactly 2 children (one text, one image) on desktop, an asymmetric layout is used: 40% width for text, 60% for images. When True, they split 50/50.
LOADINGSCREEN_IMG_INCREMENT (50) — Passed to the viewer config but not currently referenced in the JS code. Likely reserved for controlling how many images are shown per loading screen update.
MAX_LABELS (200) — Maximum number of stack labels (folder names) visible at once in the 3D viewer. Labels closest to screen center get priority. The rest are hidden to avoid clutter and maintain performance.
SCREEN_BUFFER (100) — Declared and passed to the viewer but not actively referenced in the label/rendering logic. Likely reserved for extending label visibility beyond screen edges.
COLORED_HTML_DOTS (True) — When True, the dots next to folder names in the tree/breadcrumb (representing accumulated HTML files) are colored based on each HTML file's path and SEED. When False, dots are white.
BREADCRUMB_HTML_DOTS (False) — When True, HTML propagation dots are also shown in the breadcrumb bar at the top. When False, dots only appear in the tree navigation.
SHOW_NAV_ACCESSORIES (False) — Master toggle for navigation decorations: dotfile indicators (blue/green dots), HTML propagation dots in breadcrumbs, and other nav decorative elements.
SUBMENU_CLOSE_DELAY (400) — Milliseconds to wait before closing a submenu when the mouse leaves it. Higher = more forgiving hover behavior, lower = snappier menus.
WIRE_STRAIGHT (False) — Controls the tree navigation wire style. When False, wires use curved paths (Houdini VOP-style). When True, wires are straight lines.
"



you can choose to put this file anywhere in a folder or next to images, if you dont, then the values from the defaults will be used.


defaults "

 'SPRITESHEET_SIZE': 1024 * 4,
    'SPRITE_SIZE': 256,
    'RESIZE_METHOD': Image.LANCZOS,
    
    # Image Processing Defaults
    'SHARPEN': False,
    'SHARPEN_RADIUS': 1,
    'SHARPEN_PERCENT': 20,
    'SHARPEN_THRESHOLD': 3,

    'GAUSSIAN_BLUR': False,
    'GAUSSIAN_BLUR_RADIUS': 2,
    
    'COLOR_TO_TRANSPARENT': 'blue',
    'COLOR_THRESHOLD': 30,

    'DITHERING': False,
    'DITHER_MODE': 'custom_palette',
    'DITHER_METHOD': 'ordered',
    'DITHER_COLORS': 256,
    'CUSTOM_PALETTE': ['#000000', '#FF0000', '#00FF00'],

    'MAX_GIF_FRAMES': 30,
    'GIF_SPEED': 0.6, 


    # Folder Label Defaults (Renamed & Updated)
    'IMAGE_SETTINGS_LABELS': True,       # Was IMAGE_FOLDERNAME
    'IMAGE_SETTINGS_COLOR': 'white',     # Was IMAGE_FOLDERNAME_COLOR
    'IMAGE_SETTINGS_FONTSIZE': 3,       # Was IMAGE_FOLDERNAME_FONTSIZE
    'IMAGE_SETTINGS_CUSTOMTEXT': "",     # NEW: Custom text override
    'TEXT_IMAGE_RESOLUTION': 256,        # NEW: Fixed resolution for text labels
    'LABEL_SPRITE_SIZE': 512,            # Sprite size for top/bottom label images on spritesheets
    'LOD_TARGET_SPRITE_SIZES': [None, 32, 8],  # Target sprite px per LOD level (None = original)
    'LOD_VIEWHEIGHT_THRESHOLDS': [20, 40],  # viewHeight < [0] → LOD0, < [1] → LOD1, else LOD2

    #square image processing or not
    'SQUARE_IMAGES': True,
   
    # Viewer Config
    'STACK_SPACING': 0.09,
    'STACK_DIM_OPACITY': 0.1, 
    'SEED': 2922,
    'QUICKLOAD_THRESHOLD': 100,
    'ORDERED_GRID_LAYOUT': True,
    'ROTATION_SPEED': 0.000015,
    'RANDOM_ZOOM': False,
    'ZOOM_VALUE': 0.4,
    'RANDOM_TEXTDIV_POSITION': False,
    'DIV_RATIO_HALF': False,
    'LOADINGSCREEN_IMG_INCREMENT': 50,

    #stack labels/annotations 
    'MAX_LABELS': 200,
    'SCREEN_BUFFER': 100,
    'COLORED_HTML_DOTS': True,
    'BREADCRUMB_HTML_DOTS': False,
    'SHOW_NAV_ACCESSORIES': False,
    'SUBMENU_CLOSE_DELAY': 400,
    'WIRE_STRAIGHT': False

"





"
X
"


easiest way is to put this file yourself with settings. you can comment out lines, 
you can delete lines etc. 





---


how to add 3d models?


houdini is easiest, only flipbook rendered is used, i tried opengl and karma but it took way to long to be useful. so whatever is visible in the viewpport will be shown
you can cisulize attributes, visualizers, and all viewport shading settings, etc..



static geometry

1)build a geometry in houdini and use the hda to export it out properly
2)you can also bake your texture in blender, easy baking option, and then impoort your model in houdini and apply a constant shader with that texture

"
X
"


you can also export your .custom_processing file from here

"
X
"




animated geometry
same thing as before, but you need to set the keyframes how many frame syou want. currently max is 30 but this can be altered in defaults.

the animated geometry is converted to gifs, and then layed out on a spritesheet as the other images.there is a known  bug that,  if 1 gif is not on the same spritesheet, there is a glitch (e.g. 500 frames and the full spritesheet supports only 400, then 100 frames will be glitching out since they use a differernt spritesheet. thjis is a limitation ). so if you see a glitch, perhaps lower the frames and try again

 'MAX_GIF_FRAMES': 30,


 

running the script
for testing
PROCESS_IMG_LOWRES = True


for production


PROCESS_IMG_LOWRES = False


how to push to the offical website?





in the future
displacement settings per image. this would make the geometry 3d and closed. but will require another spritesheet and more loading times
agents doing a* on the stacks. with perspective camera which we can highlight too to have aperspective view of the setup



















