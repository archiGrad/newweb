from pathlib import Path
import json
import ast
from PIL import Image, ImageDraw, ImageFont
from natsort import natsorted

# ==========================================
# GLOBAL DEFAULT CONFIGURATION
# ==========================================

DEFAULTS = {
    'SPRITESHEET_SIZE': 1024 * 4,
    'SPRITE_SIZE': 64,
    'RESIZE_METHOD': Image.LANCZOS,
    'SPRITESHEET_FORMAT': 'webp',
    
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
    'TEXT_IMAGE_RESOLUTION': 512,        # NEW: Fixed resolution for text labels

    #square image processing or not
    'SQUARE_IMAGES': True,
   
    # Viewer Config
    'STACK_SPACING': 0.09,
    'STACK_DIM_OPACITY': 0.35, 
    'SEED': 2922,
    'QUICKLOAD_THRESHOLD': 100,
    'ORDERED_GRID_LAYOUT': True,
    'ROTATION_SPEED': 0.000015,
    'RANDOM_TEXTDIV_POSITION': False,
    'LOADINGSCREEN_IMG_INCREMENT': 50,

    #stack labels/annotations 
    'MAX_LABELS': 200,
    'SCREEN_BUFFER': 100

}

# ==========================================
# CONFIGURATION PARSING
# ==========================================

def parse_custom_processing(path, current_config):
    new_config = current_config.copy()
    
    sprite_size_file = path / '.sprite_size'
    if sprite_size_file.exists():
        try:
            val = int(sprite_size_file.read_text().strip())
            new_config['SPRITE_SIZE'] = val
        except:
            print(f"Warning: Invalid .sprite_size in {path}")

    custom_file = path / '.custom_processing'
    if custom_file.exists():
        try:
            content = custom_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    if key in DEFAULTS:
                        try:
                            new_config[key] = ast.literal_eval(value)
                        except:
                            new_config[key] = value
        except Exception as e:
            print(f"Warning: Error parsing .custom_processing in {path}: {e}")
            
    return new_config


# ==========================================
# IMAGE PROCESSING FUNCTIONS
# ==========================================

def apply_filter(img, conf):
    if conf['SHARPEN']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(
            radius=conf['SHARPEN_RADIUS'],
            percent=conf['SHARPEN_PERCENT'],
            threshold=conf['SHARPEN_THRESHOLD']
        )) 

    if conf['GAUSSIAN_BLUR']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=conf['GAUSSIAN_BLUR_RADIUS']))
    
    if conf['COLOR_TO_TRANSPARENT']:
        colors = {
            'black': (0, 0, 0), 'white': (255, 255, 255), 'red': (255, 0, 0),
            'green': (0, 255, 0), 'blue': (0, 0, 255), 'yellow': (255, 255, 0),
            'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'light_gray': (192, 192, 192),
            'dark_gray': (64, 64, 64), 'orange': (255, 165, 0), 'purple': (128, 0, 128)
        }
        target = conf['COLOR_TO_TRANSPARENT']
        if target in colors:
            target_r, target_g, target_b = colors[target]
            img = img.convert('RGBA')
            pixels = img.load()
            thresh = conf['COLOR_THRESHOLD']
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]
                    if (abs(r - target_r) < thresh and 
                        abs(g - target_g) < thresh and 
                        abs(b - target_b) < thresh):
                        pixels[x, y] = (r, g, b, 0)
    
    if conf['DITHERING']:
        dither_map = {
            'floyd_steinberg': Image.Dither.FLOYDSTEINBERG,
            'ordered': Image.Dither.ORDERED,
            'none': Image.Dither.NONE
        }
        
        has_alpha = img.mode == 'RGBA'
        alpha_channel = img.split()[3] if has_alpha else None
        
        if conf['DITHER_MODE'] == 'bw':
            rgb_img = img.convert('L')
            dithered = rgb_img.convert('1', dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'color_reduce':
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(colors=conf['DITHER_COLORS'], dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'custom_palette':
            palette_colors = []
            for hex_color in conf['CUSTOM_PALETTE']:
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                palette_colors.extend([r, g, b])
            
            while len(palette_colors) < 768:
                palette_colors.extend([0, 0, 0])
            
            palette_img = Image.new('P', (1, 1))
            palette_img.putpalette(palette_colors)
            
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        if has_alpha:
            dithered = dithered.convert('RGBA')
            dithered.putalpha(alpha_channel)
        
        img = dithered
    
    return img

def resize_image(img, target_size, conf=None):
    force_square = conf.get('SQUARE_IMAGES', False) if conf else DEFAULTS['SQUARE_IMAGES']
    
    if force_square:
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), DEFAULTS['RESIZE_METHOD'])
        return img

    # Original Logic (Preserve Aspect Ratio)
    w, h = img.size
    longest = max(w, h)
    if longest != target_size:
        scale = target_size / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), DEFAULTS['RESIZE_METHOD'])
    return img

# ==========================================
# FILE SCANNING
# ==========================================



def scan_folder(path, parent_hidden=False, inherited_spacing=None, ignore=['venv', '__pycache__', '.git', 'fonts',  'spritesheets', 'images', 'backup', 'geo']):
    if path.name in ignore:
        return None
    
    images = []
    texts = []
    children = []
    grid_layout = None
    no_accum = False
    stop_accum = False
    
    manual_spacing = inherited_spacing
    
    is_hidden = parent_hidden or (path / '.hidden').exists()
    
    if path.is_dir():
        grid_file = path / '.grid_layout'
        if grid_file.exists():
            grid_layout = grid_file.read_text().strip()
        
        # Check .custom_processing for STACK_SPACING
        custom_file = path / '.custom_processing'
        if custom_file.exists():
            try:
                content = custom_file.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if '=' in line:
                        key, value = [x.strip() for x in line.split('=', 1)]
                        if key == 'STACK_SPACING':
                            try:
                                manual_spacing = ast.literal_eval(value)
                            except:
                                pass
            except:
                pass
        
        # .stack_spacing file overrides .custom_processing
        spacing_file = path / '.stack_spacing'
        if spacing_file.exists():
            try:
                manual_spacing = float(spacing_file.read_text().strip())
            except Exception as e:
                print(f"Warning: Invalid .stack_spacing in {path}: {e}")
        
        no_accum = (path / '.no_accum').exists()
        stop_accum = (path / '.stop_accum').exists()
            
        for item in natsorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name in ignore or item.name.startswith('.'): 
                continue
            if item.is_file():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    images.append(item.relative_to('.').as_posix())
                elif item.suffix.lower() == '.html':
                    texts.append(item.relative_to('.').as_posix())
            elif item.is_dir():
                child = scan_folder(item, parent_hidden=is_hidden, inherited_spacing=manual_spacing, ignore=ignore)
                if child:
                    children.append(child)
        
        all_images = images.copy()
        all_texts = texts.copy()
        for child in children:
            all_images.extend(child['ai'])
            if not child.get('na', False) and not child.get('sa', False):
                all_texts.extend(child['at'])        

    content_type = 'empty'
    if all_images and all_texts: content_type = 'mixed'
    elif all_images: content_type = 'images'
    elif all_texts: content_type = 'text'
    
    result = {
        'name': path.name,
        'path': path.relative_to('.').as_posix(),
        'type': content_type,
        'children': children,
        'ai': all_images, 
        'at': all_texts,
        'oi': images,
        'ot': texts,
        'na': no_accum,
        'sa': stop_accum,
        'hid': is_hidden,
        'msp': manual_spacing
    }
    if grid_layout: result['grid_layout'] = grid_layout
    return result


# root = scan_folder(Path('.'))
# root['name'] = Path('.').resolve().name or "Root"


# Check if the specific project folder exists and use it as the root
target_root = Path('archiGrad.io')

if target_root.exists() and target_root.is_dir():
    root = scan_folder(target_root, inherited_spacing=None)


# ==========================================
# LABEL GENERATION
# ==========================================

def load_custom_font(size):
    # 1. Check specifically for the requested font in ./fonts/
    requested_font = Path('fonts/UbuntuMono-Regular.ttf')
    if requested_font.exists():
        try:
            return ImageFont.truetype(str(requested_font), int(size))
        except IOError:
            print(f"Warning: Found {requested_font} but could not load it.")
            
    # 2. Fallback List
    font_candidates = [
        "UbuntuMono-Regular.ttf", 
        "UbuntuMono-R.ttf",
        "DejaVuSansMono.ttf", 
        "FreeMono.ttf", 
        "Consolas.ttf",
        "arial.ttf"
    ]
    
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, int(size))
        except IOError:
            continue
            
    # 3. Final Fallback
    try:
        return ImageFont.load_default(size=int(size))
    except TypeError:
        return ImageFont.load_default()

def get_dotfile_content(path):
    ignored_dotfiles = [
        '.no_accum', '.stop_accum', '.hidden', 
        '.DS_Store', '.git', '.gitignore', '__pycache__'
    ]
    
    candidates = []
    try:
        for item in path.iterdir():
            if item.is_file() and item.name.startswith('.') and item.name not in ignored_dotfiles:
                candidates.append(item)
    except Exception:
        pass
    
    if not candidates:
        return None
        
    target = sorted(candidates, key=lambda x: x.name)[0]
    
    try:
        content = target.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        if not lines:
            return None
            
        return {'name': target.name, 'lines': lines}
    except Exception as e:
        print(f"Error reading dotfile {target}: {e}")
        return None

def create_label_image(title, body_lines, color, output_path, img_resolution, font_size):
    try:
        # Use the passed resolution
        img = Image.new('RGBA', (img_resolution, img_resolution), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Use the scaled font size
        font_title = load_custom_font(int(font_size * 1.5))
        font_body = load_custom_font(int(font_size))
        
        def get_text_size(text, font):
            try:
                left, top, right, bottom = font.getbbox(text)
                return right - left, bottom - top
            except AttributeError:
                return font.getsize(text)

        # Layout Configuration
        scale_factor = img_resolution / 64.0
        padding_left = int(10 * scale_factor)
        padding_top = int(10 * scale_factor)
        
        # --- CHANGED: Set spacing to minimum (0) ---
        line_spacing = 0 
        title_body_gap = int(2 * scale_factor) if (title and body_lines) else 0
        # -------------------------------------------
        
        current_y = padding_top
        
        if title:
            draw.text((padding_left, current_y), title, fill=color, font=font_title)
            title_w, title_h = get_text_size(title, font_title)
            current_y += title_h + title_body_gap
        
        for line in body_lines:
            draw.text((padding_left, current_y), line, fill=color, font=font_body)
            line_w, line_h = get_text_size(line, font_body)
            current_y += line_h + line_spacing
            
        img.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating label {output_path}: {e}")
        return False

def manage_folder_labels(node, parent_config):
    node_path = Path(node['path'])
    current_config = parse_custom_processing(node_path, parent_config)
    
    folder_name = node['name']
    top_name = f"ZZ_{folder_name}_top.png"
    bottom_name = f"AA_{folder_name}_bottom.png"
    
    top_path = node_path / top_name
    bottom_path = node_path / bottom_name
    
    real_images = []
    for img_str in node['oi']:
        p = Path(img_str)
        if p.name not in [top_name, bottom_name]:
            real_images.append(img_str)
    
    real_images = natsorted(real_images, key=lambda x: Path(x).name)
            
    should_generate = current_config.get('IMAGE_SETTINGS_LABELS', False)
    has_real_images = len(real_images) > 0
    
    new_oi_list = []

    if should_generate and has_real_images:
        color = current_config.get('IMAGE_SETTINGS_COLOR', 'white')
        
        # Configs from user/dotfile
        base_font_size = current_config.get('IMAGE_SETTINGS_FONTSIZE', 16)
        custom_text = current_config.get('IMAGE_SETTINGS_CUSTOMTEXT', "")
        
        # FORCE High Resolution
        text_resolution = DEFAULTS['TEXT_IMAGE_RESOLUTION']
        
        # SCALE Font Size
        font_scale = text_resolution / 64.0
        effective_font_size = int(base_font_size * font_scale)
        
        # -------------------------------------------------
        # PRIORITY LOGIC
        # -------------------------------------------------
        if custom_text and custom_text.strip():
            lines = custom_text.strip().splitlines()
            top_title = ""
            top_body = lines
            bottom_title = ""
            bottom_body = lines
        else:
            dotfile_data = get_dotfile_content(node_path)
            if dotfile_data:
                top_title = dotfile_data['name']
                top_body = dotfile_data['lines']
                bottom_title = dotfile_data['name']
                bottom_body = dotfile_data['lines']
            else:
                top_title = folder_name
                top_body = ["top"]
                bottom_title = folder_name
                bottom_body = ["bottom"]
        
        if create_label_image(bottom_title, bottom_body, color, bottom_path, text_resolution, effective_font_size):
            # new_oi_list.append(str(bottom_path.relative_to('.')))
            new_oi_list.append(bottom_path.relative_to('.').as_posix())
        
        new_oi_list.extend(real_images)
        
        if create_label_image(top_title, top_body, color, top_path, text_resolution, effective_font_size):
            # new_oi_list.append(str(top_path.relative_to('.')))
            new_oi_list.append(top_path.relative_to('.').as_posix())
            
        node['oi'] = new_oi_list
        
    else:
        if top_path.exists():
            try: top_path.unlink()
            except: pass
        if bottom_path.exists():
            try: bottom_path.unlink()
            except: pass
            
        node['oi'] = real_images

    for child in node['children']:
        manage_folder_labels(child, current_config)

# Execute Label Generation
manage_folder_labels(root, DEFAULTS)


# ==========================================
# FLATTENING AND CONFIG ASSIGNMENT
# ==========================================

all_image_items = [] 

def collect_images_with_config(node, parent_config):
    node_path = Path(node['path'])
    current_config = parse_custom_processing(node_path, parent_config)
    
    for img_path in node['oi']:
        all_image_items.append({
            'path': img_path,
            'conf': current_config
        })
        
    for child in node['children']:
        collect_images_with_config(child, current_config)

collect_images_with_config(root, DEFAULTS)

all_image_items.sort(key=lambda x: (x['conf']['SPRITE_SIZE'], x['path']))

# ==========================================
# SPRITESHEET GENERATION
# ==========================================

Path('spritesheets').mkdir(exist_ok=True)
for file in Path('spritesheets').glob('*'):
    file.unlink()

sprite_data = {} 
sheet_idx = 0
current_sheet_size = 0 
sheet = None
slot_idx = 0

for item in all_image_items:
    img_path = item['path']
    conf = item['conf']
    
    target_size = conf['SPRITE_SIZE']
    sheet_dim = conf['SPRITESHEET_SIZE']
    
    sprites_per_row = sheet_dim // target_size
    sprites_per_sheet = sprites_per_row * sprites_per_row
    
    if sheet is None or target_size != current_sheet_size or slot_idx >= sprites_per_sheet:
        if sheet is not None:
            sheet.save(f'spritesheets/sprites_{sheet_idx}.{DEFAULTS["SPRITESHEET_FORMAT"]}')
            sheet_idx += 1
        
        sheet = Image.new('RGBA', (sheet_dim, sheet_dim), (0, 0, 0, 0))
        slot_idx = 0
        current_sheet_size = target_size

    speed_val = max(0.0, min(1.0, conf['GIF_SPEED']))
    gif_delay_ms = int(500 - (speed_val * 480))

    is_gif = img_path.lower().endswith('.gif')
    
    if is_gif:
        try:
            gif = Image.open(img_path)
            frame_count = min(gif.n_frames, conf['MAX_GIF_FRAMES']) 
            
            if slot_idx + frame_count > sprites_per_sheet:
                sheet.save(f'spritesheets/sprites_{sheet_idx}.{DEFAULTS["SPRITESHEET_FORMAT"]}')
                sheet_idx += 1
                sheet = Image.new('RGBA', (sheet_dim, sheet_dim), (0, 0, 0, 0))
                slot_idx = 0
            
            start_idx = slot_idx
            for frame_idx in range(frame_count):
                gif.seek(frame_idx)
                frame = gif.convert('RGBA')
                # frame = resize_image(frame, target_size)
                frame = resize_image(frame, target_size, conf)
                frame = apply_filter(frame, conf)           
    
                col = slot_idx % sprites_per_row
                row = slot_idx // sprites_per_row
                x = col * target_size
                y = row * target_size
                sheet.paste(frame, (x, y))
                slot_idx += 1
            
            sprite_data[img_path] = {
                'ss': f'spritesheets/sprites_{sheet_idx}.{DEFAULTS["SPRITESHEET_FORMAT"]}',
                'si': start_idx,
                'fc': frame_count,
                'anim': True,
                'w': target_size,
                'h': target_size,
                'sz': target_size,
                'gd': gif_delay_ms,
                'path': img_path
            }
        except Exception as e:
            print(f"Error processing GIF {img_path}: {e}")
    else:
        try:
            img = Image.open(img_path).convert('RGBA')
            # img = resize_image(img, target_size)
            img = resize_image(img, target_size, conf)
            img = apply_filter(img, conf)       
    
            col = slot_idx % sprites_per_row
            row = slot_idx // sprites_per_row
            x = col * target_size
            y = row * target_size
            sheet.paste(img, (x, y))
            
            sprite_data[img_path] = {
                'ss': f'spritesheets/sprites_{sheet_idx}.{DEFAULTS["SPRITESHEET_FORMAT"]}',
                'idx': slot_idx,
                'w': img.width,
                'h': img.height,
                'sz': target_size,
                'path': img_path
            }
            slot_idx += 1
        except Exception as e:
            print(f"Error processing Image {img_path}: {e}")

if sheet:
    sheet.save(f'spritesheets/sprites_{sheet_idx}.{DEFAULTS["SPRITESHEET_FORMAT"]}')

# ==========================================
# TREE PROCESSING & SAVING (OPTIMIZED)
# ==========================================

# 1. Assign 'gi' (Global Index) to the original sprite objects 
#    We do this BEFORE converting the tree to IDs, while we still have paths.
global_index_counter = 0

def assign_gi_and_filter(node):
    global global_index_counter
    # We filter and assign 'gi' at the same time
    
    # Process 'ai' (Active Images)
    valid_ai = []
    for path in node['ai']:
        if path in sprite_data:
            sprite_data[path]['gi'] = global_index_counter
            global_index_counter += 1
            valid_ai.append(path)
    node['ai'] = valid_ai
            
    # Process 'oi' (Other Images)
    valid_oi = []
    for path in node['oi']:
        if path in sprite_data:
            sprite_data[path]['gi'] = global_index_counter
            global_index_counter += 1
            valid_oi.append(path)
    node['oi'] = valid_oi

    for child in node['children']:
        assign_gi_and_filter(child)

assign_gi_and_filter(root)

# 2. Create the flat "Database" of all sprite objects
image_database_list = list(sprite_data.values())

# 3. Create a lookup map: Image Path -> ID (Integer)
path_to_id = { item['path']: i for i, item in enumerate(image_database_list) }

# 4. Inject IDs into the tree instead of full objects (NORMALIZATION)
def replace_images_with_ids(node):
    # 'ai' and 'oi' will now store Integers (0, 1, 2) instead of full Objects
    node['ai'] = [path_to_id[p] for p in node['ai'] if p in path_to_id]
    node['oi'] = [path_to_id[p] for p in node['oi'] if p in path_to_id]
    
    for child in node['children']:
        replace_images_with_ids(child)

replace_images_with_ids(root)

sprite_config = {
    'spritesheet_size': DEFAULTS['SPRITESHEET_SIZE'],
    'stack_spacing': DEFAULTS['STACK_SPACING'],
    'stack_dim_opacity': DEFAULTS['STACK_DIM_OPACITY'],
    'seed': DEFAULTS['SEED'],
    'loadingscreen_img_increment': DEFAULTS['LOADINGSCREEN_IMG_INCREMENT'],
    'ordered_grid_layout': DEFAULTS['ORDERED_GRID_LAYOUT'],
    'rotation_speed': DEFAULTS['ROTATION_SPEED'],
    'random_textdiv_position': DEFAULTS['RANDOM_TEXTDIV_POSITION'],
    'quickload_threshold': DEFAULTS['QUICKLOAD_THRESHOLD'],
    'max_labels': DEFAULTS['MAX_LABELS'],
    'screen_buffer': DEFAULTS['SCREEN_BUFFER']
}

# 5. Save BOTH the tree (lightweight) and the database (heavy)
# with open('data.json', 'w') as f:
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'tree': root, 
        'database': image_database_list, 
        'sprite_config': sprite_config
    }, f, indent=None) # indent=None makes the file significantly smaller

# ==========================================
# HTML GENERATION
# ==========================================


#with open('index.html', 'w') as f:
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="styles.css">

<!-- <script src="https://unpkg.com/stats.js@0.17.0/build/stats.min.js"></script> -->

<meta charset="utf-8">

            <style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    background: black; 
    color: white; 
    font-family: monospace; 
    font-size: 11px;
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

#tree {{
    position: fixed;
    top: 10px;
    left: 10px;
    min-width: 280px;
    width: max-content;
    max-height: 80vh;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
    z-index: 1000;
    background: rgba(0,0,0,0.85);
    border: 1px solid #333;
    cursor: grab;
}}

#tree-content {{
    flex: 1;
    overflow-y: auto;
}}
#tree-search {{
    width: 50%;
    padding: 4px 6px;
    margin-bottom: 6px;
    background: rgba(0,0,0,0);
    color: white;
    border: none;
    font-family: monospace;
    font-size: 11px;
    outline: none;
    box-sizing: border-box;
}}

#content {{ 
    flex: 1; 
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
            
}}
.tree-item {{ white-space: pre; }}
.tree-link {{ cursor: pointer; color: #4af; }}
.tree-link:hover {{ background: #222; }}
.content-div {{
    border-left: 1px solid #333;
    border-bottom: 1px solid #333;

    box-sizing: border-box;
    position: relative;
    overflow: hidden;
}}
.div-label {{
    position: absolute;
    top: 5px;
    left: 5px;
    background: black;
    padding: 2px 5px;
    z-index: 100;
}}
.text-content {{
    padding: 20px;
    overflow-y: auto;
    white-space: pre-wrap;
}}
#label-container {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: hidden;
}}
.stack-label {{
    position: absolute;
    top: 0;
    left: 0;
    will-change: transform;
    pointer-events: none;
    cursor: pointer;
    color: white;
    font-family: monospace;
    font-size: 11px;
    user-select: none;
}}
.stack-label span {{
    pointer-events: auto;
}}
canvas {{ display: block; width: 100%; height: 100%; }}
</style>

</head>
<body>
<div id="tree">
    <input id="tree-search" type="text" placeholder="search..." />
    <div id="tree-content"></div>
</div>
<div id="content"></div>
<script type="importmap">
{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/jsm/"
  }}
}}
</script>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
import {{ BufferGeometryUtils }} from 'three/addons/utils/BufferGeometryUtils.js';

(() => {{
    const tree = document.getElementById('tree');
    let dragging = false, ox = 0, oy = 0;
    tree.addEventListener('mousedown', (e) => {{
        if (e.target.closest('.tree-link')) return;
        dragging = true;
        ox = e.clientX - tree.offsetLeft;
        oy = e.clientY - tree.offsetTop;
        tree.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';
    }});
    document.addEventListener('mousemove', (e) => {{
        if (!dragging) return;
        tree.style.left = (e.clientX - ox) + 'px';
        tree.style.top = (e.clientY - oy) + 'px';
    }});
    document.addEventListener('mouseup', () => {{
        if (!dragging) return;
        dragging = false;
        tree.style.cursor = 'grab';
        document.body.style.userSelect = '';
    }});
}})();

(() => {{
    const searchInput = document.getElementById('tree-search');
    searchInput.addEventListener('input', () => {{
        const query = searchInput.value.toLowerCase().trim();
        const treeContent = document.getElementById('tree-content');
        if (!query) {{
            treeContent.querySelectorAll('.tree-item, .tree-children').forEach(el => el.style.display = '');
            treeContent.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
            updateCarets();
            return;
        }}
        treeContent.querySelectorAll('.tree-item').forEach(el => el.style.display = 'none');
        treeContent.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
        treeContent.querySelectorAll('.tree-link').forEach(link => {{
            if (link.textContent.toLowerCase().includes(query)) {{
                const item = link.closest('.tree-item');
                if (item) {{
                    item.style.display = '';
                    const siblingChildren = item.nextElementSibling;
                    if (siblingChildren && siblingChildren.classList.contains('tree-children')) {{
                        siblingChildren.querySelectorAll('.tree-item').forEach(el => el.style.display = '');
                        siblingChildren.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
                    }}
                }}
                let parent = item.parentElement;
                while (parent && parent !== treeContent) {{
                    if (parent.classList.contains('tree-children')) parent.style.display = 'block';
                    if (parent.classList.contains('tree-item')) parent.style.display = '';
                    parent = parent.parentElement;
                }}
            }}
        }});
        updateCarets();
    }});
    searchInput.addEventListener('mousedown', (e) => e.stopPropagation());
    searchInput.addEventListener('keydown', (e) => {{
        if (e.key === 'Enter') {{
            e.preventDefault();
            const treeContent = document.getElementById('tree-content');
            const firstVisible = treeContent.querySelector('.tree-item:not([style*="display: none"]) .tree-link:not([style*="line-through"])');
            if (firstVisible) firstVisible.click();
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input'));
        }} else if (e.key === 'Escape') {{
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input'));
            searchInput.blur();
        }}
    }});
}})();

const loader = document.createElement('div');
loader.id = 'loader';
loader.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:black;color:white;display:flex;align-items:center;justify-content:center;z-index:99999;font-size:11px;font-family:monospace;';
loader.textContent = 'initializing...';
document.body.appendChild(loader);

let progress = {{ss: 0, ssTotal: 0, stacks: 0, stacksTotal: 0, imgs: 0, imgsTotal: 0}};

function updateLoader() {{
    const l = document.getElementById('loader');
    if (!l) return;
    
    const ssPercent = progress.ssTotal > 0 ? Math.floor((progress.ss / progress.ssTotal) * 100) : 0;
    const stacksPercent = progress.stacksTotal > 0 ? Math.floor((progress.stacks / progress.stacksTotal) * 100) : 0;
    const imgsPercent = progress.imgsTotal > 0 ? Math.floor((progress.imgs / progress.imgsTotal) * 100) : 0;
    
    const makeBar = (percent) => {{
        const filled = Math.floor(percent / 5);
        const empty = 20 - filled;
        return '█'.repeat(filled) + '·'.repeat(empty);
    }};
    
    l.innerHTML = `<div style="line-height:1.8;font-family:monospace;">
        spritesheets: ${{progress.ss}}/${{progress.ssTotal}}<br>
        ${{makeBar(ssPercent)}} ${{ssPercent}}%<br>
        <br>
        stacks: ${{progress.stacks}}/${{progress.stacksTotal}}<br>
        ${{makeBar(stacksPercent)}} ${{stacksPercent}}%<br>
        <br>
        images: ${{progress.imgs}}/${{progress.imgsTotal}}<br>
        ${{makeBar(imgsPercent)}} ${{imgsPercent}}%
    </div>`;
}}

async function updateLoaderAsync() {{
    updateLoader();
    await new Promise(r => requestAnimationFrame(r));
}}

let dataTree;
let spriteConfig;
let activeScenes = [];
const textureCache = {{}};
const pendingLoads = {{}};
const stackMaterialCache = {{}};

function seededRandom(seed) {{
    let state = seed;
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
}}


async function loadSpritesheet(path) {{
    if (textureCache[path]) return textureCache[path];
    if (pendingLoads[path]) return pendingLoads[path];
    pendingLoads[path] = new Promise((resolve) => {{
        const loader = new THREE.TextureLoader();
        loader.load(path, (texture) => {{
            texture.minFilter = THREE.NearestFilter;
            texture.magFilter = THREE.NearestFilter;
            texture.generateMipmaps = false;
            textureCache[path] = texture;
            delete pendingLoads[path];
            progress.ss++;
            updateLoader();
            resolve(texture);
        }});
    }});
    return pendingLoads[path];
}}

function getStackMaterial(texturePath, stackName) {{
    const key = `${{texturePath}}::${{stackName}}`;
    if (!stackMaterialCache[key]) {{
        stackMaterialCache[key] = new THREE.MeshBasicMaterial({{
            map: textureCache[texturePath],
            side: THREE.DoubleSide,
            transparent: true,
            alphaTest: 0.1,
            opacity: 1
        }});
    }}
    return stackMaterialCache[key];
}}





fetch('data.json')
    .then(r => r.json())
    .then(async d => {{
        const db = d.database;
        dataTree = d.tree;
        spriteConfig = d.sprite_config;

        function hydrate(node) {{
            if (node.ai) node.ai = node.ai.map(id => db[id]);
            if (node.oi) node.oi = node.oi.map(id => db[id]);
            if (node.children) node.children.forEach(hydrate);
        }}
        hydrate(dataTree);

        // buildTree(dataTree, document.getElementById('tree'));
        buildTree(dataTree, document.getElementById('tree-content'));
        progress = {{ss: 0, ssTotal: 0, stacks: 0, stacksTotal: 0, imgs: 0, imgsTotal: 0}};

        const params = new URLSearchParams(window.location.search);
        const path = params.get('path');

        const targetNode = path ? findNodeByPath(dataTree, path) : dataTree;
        
        await renderContent(targetNode || dataTree);
        
        isInitialLoad = false;
        const loaderEl = document.getElementById('loader');
        if (loaderEl) loaderEl.remove();

            const hash = window.location.hash.slice(2);

        if (hash) {{

            const node = findNodeByPath(dataTree, hash);

            if (node) await renderContent(node);

        }}

    }});











window.addEventListener('hashchange', () => {{
    const hash = window.location.hash.slice(2);
    const node = hash ? findNodeByPath(dataTree, hash) : dataTree;
    if (node) renderContent(node);
}});

function countDescendants(node) {{
    let count = 0;
    if (node.children) {{
        for (const child of node.children) {{
            count += 1 + countDescendants(child);
        }}
    }}
    return count;
}}

function buildTree(node, container, depth = 0, isLast = true, prefix = '') {{
    const connector = isLast ? '└ ' : '├ ';
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    const link = document.createElement('span');
    link.className = 'tree-link';
    
    const hasChildren = node.children && node.children.length > 0;
    const caretHtml = hasChildren ? '<span class="tree-caret">+</span> ' : '';
    const saDot = node.sa ? ' <span style="color:#ffffff;font-size:5px;vertical-align:middle;">●</span>' : '';
    const desc = countDescendants(node);
    const countLabel = desc > 0 ? ` <span style="color:#666;font-size:0.85em">(${{desc}})</span>` : '';
    link.innerHTML = caretHtml + node.name + saDot + countLabel;
    link.dataset.path = node.path;
    
    if (node.hid) {{
        link.style.textDecoration = 'line-through';
        link.style.color = '#666';
        link.style.cursor = 'not-allowed';
        link.title = 'Hidden';
    }} else {{
        link.onclick = (e) => {{
            e.stopPropagation();
            const isActive = currentNode && currentNode.path === node.path;
            if (!isActive) {{
                renderContent(node);
                updateTreeColors();
                if (hasChildren) {{
                    const childContainer = item.nextElementSibling;
                    if (childContainer && childContainer.classList.contains('tree-children')) {{
                        childContainer.style.display = 'block';
                    }}
                }}
            }} else if (hasChildren) {{
                const childContainer = item.nextElementSibling;
                if (childContainer && childContainer.classList.contains('tree-children')) {{
                    childContainer.style.display = childContainer.style.display === 'none' ? 'block' : 'none';
                }}
            }}
            updateCarets();
        }};
    }}
    
    item.appendChild(link);
    container.appendChild(item);
    
    if (hasChildren) {{
        const childContainer = document.createElement('div');
        childContainer.className = 'tree-children';
        childContainer.style.display = 'none';
        const newPrefix = prefix + (isLast ? '  ' : '│ ');
        node.children.forEach((child, i) => {{
            buildTree(child, childContainer, depth + 1, i === node.children.length - 1, newPrefix);
        }});
        container.appendChild(childContainer);
    }}
}}

function updateCarets() {{
    document.querySelectorAll('.tree-caret').forEach(caret => {{
        const item = caret.closest('.tree-item');
        if (item) {{
            const childContainer = item.nextElementSibling;
            if (childContainer && childContainer.classList.contains('tree-children')) {{
                caret.textContent = childContainer.style.display === 'none' ? '+' : '-';
            }}
        }}
    }});
}}

function getDepthColor(depth) {{
    const colors = ['#4f4', '#5e5', '#6d6', '#7c7', '#8b8', '#9a9', '#a9a', '#b8b', '#c7c', '#d6d'];
    return colors[Math.min(depth, 9)];
}}
            


function updateTreeColors() {{
    if (!currentNode) return;
    
    // Get all ancestor paths
    const ancestorPaths = [];
    const pathParts = currentNode.path.split('/');
    for (let i = 1; i < pathParts.length; i++) {{
        ancestorPaths.push(pathParts.slice(0, i).join('/'));
    }}
    
    // Get all descendant paths
    const descendantPaths = [];
    function collectDescendants(node) {{
        node.children.forEach(child => {{
            descendantPaths.push(child.path);
            collectDescendants(child);
        }});
    }}
    if (currentNode) collectDescendants(currentNode);
    
    // Expand tree to reveal current node
    const revealPaths = [...ancestorPaths, currentNode.path];
    document.querySelectorAll('.tree-link').forEach(link => {{
        const linkPath = link.dataset.path;
        if (revealPaths.includes(linkPath)) {{
            const childContainer = link.closest('.tree-item')?.nextElementSibling;
            if (childContainer && childContainer.classList.contains('tree-children')) {{
                childContainer.style.display = 'block';
            }}
        }}
    }});

    // Apply colors
    document.querySelectorAll('.tree-link').forEach(link => {{
        const linkPath = link.dataset.path;
        
        if (link.style.textDecoration === 'line-through') {{
            link.style.color = '#666';
        }} else if (linkPath === currentNode.path) {{
            link.style.color = '#44f'; // Selected: blue
        }} else if (ancestorPaths.includes(linkPath) || descendantPaths.includes(linkPath)) {{
            link.style.color = 'white'; // Parents and children: white
        }} else {{
            link.style.color = '#444'; // Others: grey
        }}
    }});
    updateCarets();
}}
            

function disposeScene(sceneData) {{
    if (sceneData.animationId) cancelAnimationFrame(sceneData.animationId);
    if (sceneData.resizeHandler) window.removeEventListener('resize', sceneData.resizeHandler);
    if (sceneData.labelContainer && sceneData.labelContainer.parentNode) {{
        sceneData.labelContainer.parentNode.removeChild(sceneData.labelContainer);
    }}
    if (sceneData.countDiv && sceneData.countDiv.parentNode) {{
        sceneData.countDiv.parentNode.removeChild(sceneData.countDiv);
    }}
    if (sceneData.renderer) {{
        sceneData.renderer.forceContextLoss();
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {{
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }}
    }}
    if (sceneData.scene) {{
        sceneData.scene.traverse((object) => {{
            if (object.geometry) object.geometry.dispose();
        }});
        sceneData.scene.clear();
    }}
}}

async function createThreeScene(container, images, node) {{
    const scene = new THREE.Scene();
    const grouped = {{}};
    const stackGroups = {{}};

    const SPRITESHEET_SIZE = spriteConfig.spritesheet_size;
    const STACK_SPACING = spriteConfig.stack_spacing;
    const STACK_DIM_OPACITY = spriteConfig.stack_dim_opacity;
    const SEED = spriteConfig.seed;
    const ORDERED_GRID_LAYOUT = spriteConfig.ordered_grid_layout;
    const ROTATION_SPEED = spriteConfig.rotation_speed;

    images.forEach(imgData => {{
        const parts = imgData.path.split('/');
        const folder = parts.slice(0, -1).join('/') || 'root';
        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgData);
    }});
    
    const folders = Object.keys(grouped);
    folders.forEach(folder => {{ grouped[folder].sort((a, b) => a.gi - b.gi); }});
   
    progress.imgsTotal += images.length;
    progress.stacksTotal += folders.length;
    const uniqueSS = new Set(images.map(i => i.ss));
    progress.ssTotal += uniqueSS.size;
    uniqueSS.forEach(ss => {{ if (textureCache[ss]) progress.ss++; }});
    updateLoader();
 
    const baseGeometry = new THREE.PlaneGeometry(1, 1);
    
    const spacing = 1.5;
    let cols, rows, offsetX, offsetZ;
    let gridGroups;
    
    if (node.grid_layout) {{
        const parts = node.grid_layout.split('x');
        cols = parseInt(parts[0]);
        rows = parseInt(parts[1]);
        offsetX = (cols - 1) * spacing / 2;
        offsetZ = (rows - 1) * spacing / 2;
    }} else {{
        gridGroups = [];
        const processedFolders = new Set();
        function collectGridChildren(n) {{
            if (n.hid) return; 
            if (n.grid_layout && n.ai.length > 0) {{
                const childFolders = folders.filter(f => f.startsWith(n.path + '/') || f === n.path);
                const [gCols, gRows] = ORDERED_GRID_LAYOUT ? n.grid_layout.split('x').map(Number) : [1, 1];
                gridGroups.push({{ folders: childFolders, cols: gCols, rows: gRows, path: n.path }});
                childFolders.forEach(f => processedFolders.add(f));
            }} else if (n.children.length > 0) {{
                n.children.forEach(child => collectGridChildren(child));
            }} else if (n.ai.length > 0) {{
                const childFolders = folders.filter(f => f.startsWith(n.path + '/') || f === n.path);
                gridGroups.push({{ folders: childFolders, cols: 1, rows: 1, path: n.path }});
                childFolders.forEach(f => processedFolders.add(f));
            }}
        }}
        node.children.forEach(child => collectGridChildren(child));
        
        if (gridGroups.length > 0) {{
            const occupiedGrid = new Map();
            const isOccupied = (gx, gy, w, h) => {{
                for (let dy = 0; dy < h; dy++) {{
                    for (let dx = 0; dx < w; dx++) {{
                        if (occupiedGrid.has(`${{gx + dx}},${{gy + dy}}`)) return true;
                    }}
                }}
                return false;
            }};
            const occupy = (gx, gy, w, h) => {{
                for (let dy = 0; dy < h; dy++) {{
                    for (let dx = 0; dx < w; dx++) {{
                        occupiedGrid.set(`${{gx + dx}},${{gy + dy}}`, true);
                    }}
                }}
            }};
            const findSpiralPosition = (w, h) => {{
                if (occupiedGrid.size === 0) return {{ x: 0, y: 0 }};
                let radius = 1;
                while (radius < 100) {{
                    for (let dy = -radius; dy <= radius; dy++) {{
                        for (let dx = -radius; dx <= radius; dx++) {{
                            if (Math.abs(dx) === radius || Math.abs(dy) === radius) {{
                                if (!isOccupied(dx, dy, w, h)) return {{ x: dx, y: dy }};
                            }}
                        }}
                    }}
                    radius++;
                }}
                return {{ x: 0, y: 0 }};
            }};
            gridGroups.forEach(group => {{
                const pos = findSpiralPosition(group.cols, group.rows);
                group.gridX = pos.x;
                group.gridY = pos.y;
                occupy(pos.x, pos.y, group.cols, group.rows);
            }});
            let minGridX = Infinity, maxGridX = -Infinity;
            let minGridZ = Infinity, maxGridZ = -Infinity;
            gridGroups.forEach(group => {{
                minGridX = Math.min(minGridX, group.gridX);
                maxGridX = Math.max(maxGridX, group.gridX + group.cols - 1);
                minGridZ = Math.min(minGridZ, group.gridY);
                maxGridZ = Math.max(maxGridZ, group.gridY + group.rows - 1);
            }});
            offsetX = ((maxGridX + minGridX) / 2) * spacing;
            offsetZ = ((maxGridZ + minGridZ) / 2) * spacing;
        }} else {{
            cols = Math.ceil(Math.sqrt(folders.length));
            rows = Math.ceil(folders.length / cols);
            offsetX = (cols - 1) * spacing / 2;
            offsetZ = (rows - 1) * spacing / 2;
        }}
    }}

 let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    
    const calculateBounds = (x, z) => {{
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minZ = Math.min(minZ, z);
        maxZ = Math.max(maxZ, z);
    }};
    const folderPositions = {{}};
    
    // --- 2. Iterate to Calculate Scene Size ---
    if (node.grid_layout) {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const x = col * spacing - offsetX;
            const z = row * spacing - offsetZ;
            folderPositions[folder] = {{x, z}};
            calculateBounds(x, z);
        }});
    }} else if (gridGroups && gridGroups.length > 0) {{
        gridGroups.forEach(group => {{
            group.folders.forEach((folder, localIdx) => {{
                const row = Math.floor(localIdx / group.cols);
                const col = localIdx % group.cols;
                const x = (group.gridX + col) * spacing - offsetX;
                const z = (group.gridY + row) * spacing - offsetZ;
                folderPositions[folder] = {{x, z}};
                calculateBounds(x, z);
            }});
        }});
    }} else {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const x = col * spacing - offsetX;
            const z = row * spacing - offsetZ;
            folderPositions[folder] = {{x, z}};
            calculateBounds(x, z);
        }});
    }}

    const meshMaxSize = 1.5 * 1.5;
    const geomWidth = maxX - minX + meshMaxSize;
    const geomDepth = maxZ - minZ + meshMaxSize;
    
    // Add margin (was 15 previously)
    const maxSceneDim = Math.max(geomWidth, geomDepth) + 5;

    // Calculate Aspect Ratio from the Container
    const aspectRatio = container.clientWidth / container.clientHeight;

    // FIT LOGIC: 
    // If Portrait (aspect < 1), div is narrow -> Zoom out (increase frustum) to fit width.
    // If Landscape (aspect >= 1), div is wide -> Height is the limiter, use maxSceneDim.
    const fitFrustumSize = aspectRatio < 1 ? maxSceneDim / aspectRatio : maxSceneDim;

    // RANDOM ZOOM LOGIC:
    const seed = images.map(img => img.gi).reduce((a, b) => a + b, 0);
    const rand = seededRandom(seed * SEED);

    let randomZoom;
    if (rand < 0.33) {{
        randomZoom = 0.1; // Close Up
    }} else if (rand < 0.66) {{
        randomZoom = 0.4; // Mid Range
    }} else {{
        randomZoom = 1.0; // Full Fit
    }}
    
    // Debug Log (Uses correct Python f-string syntax: ${{var}})
    console.log(`DEBUG: Seed=${{seed}}, Random=${{rand.toFixed(2)}}, Zoom=${{randomZoom.toFixed(2)}}`);


    // Apply the random multiplier to the perfect fit
    const frustumSize = fitFrustumSize * randomZoom;

    // --- 4. Create Camera ---
    const camera = new THREE.OrthographicCamera(
        frustumSize * aspectRatio / -2,
        frustumSize * aspectRatio / 2,
        frustumSize / 2,
        frustumSize / -2,
        0.1,
        1000
    );
    
    const renderer = new THREE.WebGLRenderer({{ 
        alpha: true, 
        antialias: true,
        powerPreference: 'high-performance'
    }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enablePan = true;

    const navButtons = document.createElement('div');
    navButtons.style.cssText = 'position:absolute;top:5px;right:5px;display:flex;gap:5px;z-index:100';
    const createButton = () => {{
        const btn = document.createElement('button');
        btn.style.cssText = 'color:#fff;border:none;padding:3px;cursor:pointer;border-radius:50%';
        return btn;
    }};
    const topBtn = createButton(); const rightBtn = createButton();
    const bottomBtn = createButton(); const leftBtn = createButton();
    navButtons.append(topBtn, rightBtn, bottomBtn, leftBtn);
    container.appendChild(navButtons);

   
    let maxStackHeight = 0;
    folders.forEach(folder => {{
        // Find the specific node for this folder to check for custom spacing
        const folderNode = findNodeByPath(dataTree, folder);
        const localSpacing = (folderNode && folderNode.msp != null) ? folderNode.msp : STACK_SPACING;
        
        maxStackHeight = Math.max(maxStackHeight, grouped[folder].length * localSpacing);
    }});
    const midHeight = maxStackHeight / 2;

    topBtn.onclick = () => {{ camera.position.set(0.01, midHeight + 15, 0); controls.target.set(0, midHeight, 0); controls.update(); }};
    rightBtn.onclick = () => {{ camera.position.set(15, midHeight + 0.3, 0.0); controls.target.set(0, midHeight, 0); controls.update(); }};
    bottomBtn.onclick = () => {{ camera.position.set(0.01, midHeight - 15, 0); controls.target.set(0, midHeight, 0); controls.update(); }};
    leftBtn.onclick = () => {{ camera.position.set(-15, midHeight + 0.3, 0.0); controls.target.set(0, midHeight, 0); controls.update(); }};

    camera.position.set(10, 10 + midHeight, 10);
    controls.target.set(0, midHeight, 0);

    const labelContainer = document.createElement('div');
    labelContainer.id = 'label-container';
    container.appendChild(labelContainer);

 
    const toggleBtn = document.createElement('button');
    toggleBtn.style.cssText = 'position:absolute;bottom:5px;left:5px;background:#44f;border:none;width:8px;height:8px;border-radius:50%;cursor:pointer;padding:0;z-index:100';
    let labelsVisible = true;
    toggleBtn.onclick = () => {{
        labelsVisible = !labelsVisible;
        labelContainer.style.display = labelsVisible ? 'block' : 'none';
        toggleBtn.style.background = labelsVisible ? '#44f' : '#f44';
    }};
    container.appendChild(toggleBtn);

    const countDiv = document.createElement('div');
    countDiv.style.cssText = 'position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;';
    container.appendChild(countDiv);

    let loadedStacks = 0;
    let loadedImages = 0;
    const totalStacks = folders.length;
    const totalImages = images.length;

    const updateCount = () => {{
        const downColor = currentNode && currentNode.children.length > 0 ? '#ffffff' : '#000';
        const gridInfo = node.grid_layout ? ` [${{node.grid_layout}}]` : '';
        countDiv.innerHTML = `zoom: ${{randomZoom.toFixed(2)}}${{gridInfo}} | ${{loadedStacks + 1}}/${{totalStacks}} stacks | ${{loadedImages}}/${{totalImages}} images`;
    }};
    updateCount();
    countDiv.addEventListener('click', (e) => {{
        if (e.target.id === 'nav-up') {{
            if (currentNode && currentNode.path) {{
                const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                renderContent(parentNode);
            }}
        }} else if (e.target.id === 'nav-down') {{
            if (currentNode && currentNode.children.length > 0) renderContent(currentNode.children[0]);
        }}
    }});

    const stackLabels = [];
    let currentFocusedParent = null;
    function focusStackGroup(parentFolder) {{
        if (currentFocusedParent === parentFolder) {{
            unfocusAll();
            currentFocusedParent = null;
        }} else {{
            for (const [folder, data] of Object.entries(stackGroups)) {{
                if (folder.startsWith(parentFolder + '/') || folder === parentFolder) {{
                    data.material.opacity = 1.0;
                }} else {{
                    data.material.opacity = STACK_DIM_OPACITY;
                }}
            }}
            currentFocusedParent = parentFolder;
        }}
    }}
    function unfocusAll() {{
        for (const [folder, data] of Object.entries(stackGroups)) {{
            data.material.opacity = 1.0;
        }}
    }}

    const loadingPromise = (async () => {{
        const allSpritesheets = new Set();
        folders.forEach(folder => {{
            grouped[folder].forEach(img => allSpritesheets.add(img.ss));
        }});
        
        await Promise.all([...allSpritesheets].map(ss => loadSpritesheet(ss)));
        
        for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {{
            const folderName = folders[stackIdx];


            // --- NEW: Retrieve Custom Spacing for this specific stack ---
            const folderNode = findNodeByPath(dataTree, folderName);
            const localSpacing = (folderNode && folderNode.msp != null) ? folderNode.msp : STACK_SPACING;
            // ------------------------------------------------------------


            const stackImages = grouped[folderName];
            const pos = folderPositions[folderName];
            const xPos = pos.x;
            const zPos = pos.z;

            const stackGroup = new THREE.Group();
            let stackMaterial = null;
            const mergeBuckets = {{}};
            const animObjects = [];

            for (let i = 0; i < stackImages.length; i++) {{
                const imgData = stackImages[i];
                if (!stackMaterial) stackMaterial = getStackMaterial(imgData.ss, folderName);
                
                const aspect = imgData.w / imgData.h;
                const height = 1.5;
                const width = height * aspect;

                const y = i * localSpacing;
                const matrix = new THREE.Matrix4();
                const position = new THREE.Vector3(xPos, y, zPos);
                const rotation = new THREE.Euler(Math.PI / 2, Math.PI, Math.PI);
                const quaternion = new THREE.Quaternion().setFromEuler(rotation);
                const scale = new THREE.Vector3(width, height, 1);
                matrix.compose(position, quaternion, scale);
                
                const currentSpriteSize = imgData.sz; 
                const SPRITES_PER_ROW = Math.floor(SPRITESHEET_SIZE / currentSpriteSize);

                if (imgData.anim) {{
                    const mesh = new THREE.Mesh(baseGeometry.clone(), stackMaterial);
                    mesh.applyMatrix4(matrix);
                    
                    mesh.userData = {{ imgData: imgData, spritesheet: imgData.ss, spritesPerRow: SPRITES_PER_ROW }};
                    mesh.onBeforeRender = function() {{
                        const frame = Math.floor(Date.now() / this.userData.imgData.gd) % this.userData.imgData.fc;
                        const idx = this.userData.imgData.si + frame;
                        const rowLen = this.userData.spritesPerRow;
                        const sprite_col = idx % rowLen;
                        const sprite_row = Math.floor(idx / rowLen);
                        
                        const size = this.userData.imgData.sz;
                        const u_start = (sprite_col * size) / SPRITESHEET_SIZE;
                        const u_end = u_start + size / SPRITESHEET_SIZE;
                        const v_start = 1 - ((sprite_row + 1) * size) / SPRITESHEET_SIZE;
                        const v_end = 1 - (sprite_row * size ) / SPRITESHEET_SIZE;
                        
                        const uvs = this.geometry.attributes.uv;
                        uvs.setXY(0, u_start, v_end);
                        uvs.setXY(1, u_end, v_end);
                        uvs.setXY(2, u_start, v_start);
                        uvs.setXY(3, u_end, v_start);
                        uvs.needsUpdate = true;
                    }};
                    animObjects.push(mesh);
                }} else {{
                    if (!mergeBuckets[imgData.ss]) mergeBuckets[imgData.ss] = [];
                    
                    const geometry = baseGeometry.clone();
                    geometry.applyMatrix4(matrix);
                    
                    const idx = imgData.idx;
                    const sprite_col = idx % SPRITES_PER_ROW;
                    const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                    const u_start = (sprite_col * currentSpriteSize) / SPRITESHEET_SIZE;
                    const u_end = u_start + imgData.w / SPRITESHEET_SIZE;
                    const v_start = 1 - ((sprite_row + 1) * currentSpriteSize) / SPRITESHEET_SIZE;
                    const v_end = 1 - (sprite_row * currentSpriteSize) / SPRITESHEET_SIZE;
                    
                    const uvs = geometry.attributes.uv;
                    uvs.setXY(0, u_start, v_end);
                    uvs.setXY(1, u_end, v_end);
                    uvs.setXY(2, u_start, v_start);
                    uvs.setXY(3, u_end, v_start);
                    
                    mergeBuckets[imgData.ss].push(geometry);
                }}
                loadedImages++;
                progress.imgs++;
            }}

            for (const [ss, geoms] of Object.entries(mergeBuckets)) {{
                if (geoms.length > 0) {{
                    const mergedGeo = BufferGeometryUtils.mergeBufferGeometries(geoms);
                    const mat = getStackMaterial(ss, folderName);
                    const mesh = new THREE.Mesh(mergedGeo, mat);
                    stackGroup.add(mesh);
                    geoms.forEach(g => g.dispose());
                }}
            }}
            animObjects.forEach(obj => stackGroup.add(obj));
            scene.add(stackGroup);
            stackGroups[folderName] = {{ group: stackGroup, material: stackMaterial }};

            updateCount();
            loadedStacks++;
            progress.stacks++;
            if (progress.stacks % 5 === 0) await updateLoaderAsync();

            // const topY = (stackImages.length - 1) * STACK_SPACING;
            const topY = (stackImages.length - 1) * localSpacing;
            const worldPos = new THREE.Vector3(xPos, topY, zPos);
            const label = document.createElement('span');


            const currentPath = currentNode ? currentNode.path : '';
            const currentFolderName = currentPath ? currentPath.split('/').pop() : 'root';
            let navHtml = '';

            const relativePath = folderName.startsWith(currentPath) && currentPath ? folderName.slice(currentPath.length + 1) : folderName;
            const pathParts = relativePath.split('/').filter(p => p);
            const displayParts = currentPath ? ['..', currentFolderName, ...pathParts] : pathParts;

            // 1. Root (<<) - Go back all the way
            // if (currentPath) {{
                 // navHtml += `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:#f44;pointer-events:auto" data-path="">&lt;&lt;</span>/`;
            //}}



            // 2. Parent (<) - Go back 1 level
            if (currentPath) {{
                const parentPath = currentPath.split('/').slice(0, -1).join('/');
                navHtml += `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:white;pointer-events:auto" data-path="${{parentPath}}">&lt;</span>/`;
            }}
            // 3. Focus (Current Folder Name) - THIS SHOULD BE BLUE
            navHtml += `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:#44f;pointer-events:auto" data-path="${{currentPath}}">${{currentFolderName}}</span>`;

            // 4. Intermediates (>) and Leaf (>)
            let relPath = '';
            if (folderName.startsWith(currentPath + '/')) {{
                relPath = folderName.slice(currentPath.length + 1);
            }} else if (currentPath === '') {{
                relPath = folderName;
            }}

            const relParts = relPath.split('/').filter(p => p);

            if (relParts.length > 0) {{
                navHtml += '/';
                const childName = relParts[0];
                const childPath = currentPath ? currentPath + '/' + childName : childName;
                navHtml += `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:white;pointer-events:auto" data-path="${{childPath}}">&gt;</span>`;
            }}








            // 5. Image Count
            navHtml += `<span style="background:black;padding:2px 4px;font-size:9px;margin-left:2px;pointer-events:auto">${{stackImages.length}}</span>`;
            
            label.innerHTML = navHtml;
            label.className = 'stack-label';
            
            label.addEventListener('wheel', (e) => {{ e.stopPropagation(); renderer.domElement.dispatchEvent(new WheelEvent('wheel', e)); }}, {{ passive: false }});
            labelContainer.appendChild(label);
            stackLabels.push({{ element: label, position: worldPos, xPos, zPos, folderName }});
            
            label.querySelectorAll('span[data-path]').forEach(span => {{
                span.onclick = (e) => {{
                    e.stopPropagation();
                    const clickedPath = span.dataset.path;
                    const clickedNode = findNodeByPath(dataTree, clickedPath);
                    if (clickedNode && clickedNode.path === currentNode.path) {{
                        const parentFolder = folderName.split('/').slice(0, -1).join('/');
                        focusStackGroup(parentFolder);
                    }} else if (clickedNode) renderContent(clickedNode);
                }};
            }});
        }}
    }})();

    // const stats = new Stats();
    // stats.showPanel(0);
    // container.appendChild(stats.dom);
    // stats.dom.style.position = 'absolute';
    // stats.dom.style.top = '30px';
    // stats.dom.style.left = '5px';

    const resizeHandler = () => {{
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }};

    // const sceneData = {{ scene, renderer, camera, controls, animationId: null, resizeHandler, stats, labelContainer, countDiv, stackGroups, focusStackGroup, unfocusAll }};
    const sceneData = {{ scene, renderer, camera, controls, animationId: null, resizeHandler, labelContainer, countDiv, stackGroups, focusStackGroup, unfocusAll }};

    const frustum = new THREE.Frustum();
    const cameraViewProjectionMatrix = new THREE.Matrix4();

    let frameCount = 0;
    
    // OPTIMIZATION SETTINGS


    const MAX_LABELS =  spriteConfig.max_labels;
    const SCREEN_BUFFER = spriteConfig.screen_buffer;

    function animate() {{
        // stats.begin();
        sceneData.animationId = requestAnimationFrame(animate);
        controls.update();
        const rotationAngle = Date.now() * ROTATION_SPEED;
        scene.rotation.y = rotationAngle;
        
        // Frustum culling for stacks (every 5 frames)
        if (frameCount % 5 === 0) {{
            camera.updateMatrixWorld();
            cameraViewProjectionMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
            frustum.setFromProjectionMatrix(cameraViewProjectionMatrix);
            for (const [folder, data] of Object.entries(stackGroups)) {{
                if (!data.boundingBox) data.boundingBox = new THREE.Box3().setFromObject(data.group);
                data.group.visible = frustum.intersectsBox(data.boundingBox);
            }}
        }}
        
        // OPTIMIZED LABEL UPDATE (Every frame, but efficient)
        if (labelsVisible) {{
            const cWidth = container.clientWidth;
            const cHeight = container.clientHeight;
            const cCenterX = cWidth / 2;
            const cCenterY = cHeight / 2;

            const labelCandidates = [];

            const cosR = Math.cos(rotationAngle);
            const sinR = Math.sin(rotationAngle);

            // 1. Calculate positions and filter roughly
            for (let i = 0; i < stackLabels.length; i++) {{
                const lbl = stackLabels[i];
                
                // Manual World Rotation
                const rX = lbl.xPos * cosR + lbl.zPos * sinR;
                const rZ = -lbl.xPos * sinR + lbl.zPos * cosR;
                
                // Quick Depth Check (is it behind camera?)
                // Simple heuristic since we know camera is roughly at +Z
                // But camera rotates. So we use projection.
                
                const vec = new THREE.Vector3(rX, lbl.position.y, rZ);
                vec.project(camera);
                
                // vec.x and vec.y are now -1 to 1
                // Check bounds with buffer
                if (vec.z < 1 && vec.x >= -1.2 && vec.x <= 1.2 && vec.y >= -1.2 && vec.y <= 1.2) {{
                    const screenX = (vec.x * 0.5 + 0.5) * cWidth;
                    const screenY = (-(vec.y * 0.5) + 0.5) * cHeight;
                    
                    // Calculate distance to center of screen for priority
                    const dist = Math.abs(screenX - cCenterX) + Math.abs(screenY - cCenterY);
                    
                    labelCandidates.push({{
                        el: lbl.element,
                        x: screenX,
                        y: screenY,
                        d: dist
                    }});
                }} else {{
                    if (lbl.element.style.display !== 'none') lbl.element.style.display = 'none';
                }}
            }}

            // 2. Sort by distance to center screen
            labelCandidates.sort((a, b) => a.d - b.d);

            // 3. Render top N, hide rest
            for (let i = 0; i < labelCandidates.length; i++) {{
                const cand = labelCandidates[i];
                if (i < MAX_LABELS) {{
                    if (cand.el.style.display !== 'block') cand.el.style.display = 'block';
                    // Use Transform instead of Top/Left to avoid reflows
                    cand.el.style.transform = `translate3d(${{cand.x.toFixed(1)}}px, ${{cand.y.toFixed(1)}}px, 0)`;
                }} else {{
                    if (cand.el.style.display !== 'none') cand.el.style.display = 'none';
                }}
            }}
        }}

        frameCount++;
        renderer.render(scene, camera);
        // stats.end();
    }}
    animate();

    activeScenes.push(sceneData);
    window.addEventListener('resize', resizeHandler);

    await loadingPromise;
    return sceneData;
}}
 
async function loadText(path) {{
    const res = await fetch(path);
    return await res.text();
}}

function findNodeByPath(node, targetPath) {{
    if (node.path === targetPath || node.name === targetPath) return node;
    for (const child of node.children) {{
        const found = findNodeByPath(child, targetPath);
        if (found) return found;
    }}
    return null;
}}

let currentNode = null;
let isInitialLoad = true;

function updateURL(node) {{
    const path = node.path || '';
    history.pushState(null, '', '?path=' + encodeURIComponent(path)); 
}}

async function renderContent(node) {{
    if (!isInitialLoad) updateURL(node);
    const RANDOM_TEXTDIV_POSITION = spriteConfig.random_textdiv_position;
    const SEED = spriteConfig.seed;

    updateURL(node);
    currentNode = node;
    updateTreeColors();
    
    for (const key in stackMaterialCache) {{
        if (stackMaterialCache[key]) stackMaterialCache[key].opacity = 1.0;
    }}
    
    activeScenes.forEach(disposeScene);
    activeScenes = [];
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
   
    const scenePromises = []; 
    let children = node.children.length > 0 ? node.children : [node];
    children = children.map(child => {{
        if (child.sa || node.sa) return {{ ...child, at: [] }};
        return child;
    }});
    children = children.filter(child => (child.ai.length > 0 || child.at.length > 0) && !child.hid);
    
    const count = children.length;
    const cols = Math.ceil(Math.sqrt(count));
    
    for (const child of children) {{
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.width = `calc(${{100/cols}}% - 2px)`;
        div.style.height = count <= 2 ? '100%' : `calc(${{100/Math.ceil(count/cols)}}% - 2px)`;

        const label = document.createElement('div');
        label.className = 'div-label';
        const pathParts = child.path.split('/');
        label.innerHTML = pathParts.map((part, idx) => {{
    const partPath = pathParts.slice(0, idx + 1).join('/');
    let color = 'white';
    if (currentNode && partPath === currentNode.path) {{
        color = '#44f';
    }}
            
const pNode = findNodeByPath(dataTree, partPath);
    const dot = (pNode && pNode.na) ? '<span style="color:#f44;font-size:9px;vertical-align:middle;margin-left:1px;">●</span>' : '';
    
    return `<span style="color:${{color}};cursor:pointer" data-path="${{partPath}}">${{part}}${{dot}}</span>`;
}}).join('/');
            
        label.style.pointerEvents = 'auto';
        label.querySelectorAll('span[data-path]').forEach(span => {{
            span.onclick = (e) => {{
                e.stopPropagation();
                const node = findNodeByPath(dataTree, span.dataset.path);
                if (node) renderContent(node);
            }};
        }});

        div.appendChild(label);

        if (child.ai.length > 0 && child.at.length > 0) {{
            div.style.display = 'flex';
            div.style.flexDirection = 'row';
            
            // 1. Create a Wrapper for Text + Nav (This stays fixed)
            const textWrapper = document.createElement('div');
            textWrapper.style.flex = '3';
            textWrapper.style.position = 'relative'; // Anchor for the Nav
            textWrapper.style.borderLeft = '1px solid #333';
            textWrapper.style.boxSizing = 'border-box';
            //textWrapper.style.border = '1px solid white';
            textWrapper.style.overflow = 'hidden';   // The wrapper does NOT scroll

            // 2. Create the Scrollable Text Area
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.width = '100%';
            textDiv.style.height = '100%';
            textDiv.style.overflowY = 'auto'; // The text scrolls INSIDE here
            textDiv.style.position = 'absolute'; // Fill the wrapper
            textDiv.style.top = '0';
            textDiv.style.left = '0';

            let htmlContent = '';
            for (const path of child.at) {{
                htmlContent += await loadText(path);
            }}
            
textDiv.innerHTML = htmlContent;

const scriptTags = textDiv.querySelectorAll('script');
scriptTags.forEach(oldScript => {{
    const newScript = document.createElement('script');
    newScript.textContent = oldScript.textContent;
    oldScript.parentNode.replaceChild(newScript, oldScript);
}});

            // 3. Create the Nav separately (Sibling to textDiv, child of Wrapper)
            const navDiv = document.createElement('div');
            
            const hasParent = currentNode.path.split('/').length > 1;
            const firstChildWithText = currentNode.children?.find(c => c.at.length > 0);
            const leftColor = hasParent ? '#f44' : '#44f';
            const rightColor = firstChildWithText ? '#4f4' : '#44f';

            navDiv.innerHTML = `
                <span style="cursor:pointer;padding:0 5px;user-select:none;color:${{leftColor}}" class="text-nav-left">&lt;</span>
                <span style="cursor:pointer;padding:0 5px;user-select:none;color:${{rightColor}}" class="text-nav-right">&gt;</span>
            `;
            navDiv.style.cssText = 'position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;padding:2px 5px;z-index:100';

            // 4. Assemble
            textWrapper.appendChild(textDiv);
            textWrapper.appendChild(navDiv);

            // Re-attach listeners (query from navDiv directly)
            const navLeft = navDiv.querySelector('.text-nav-left');
            const navRight = navDiv.querySelector('.text-nav-right');
            
            navLeft.onclick = () => {{
                if (currentNode && currentNode.path) {{
                    const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                    const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                    if (parentNode && parentNode.at.length > 0) renderContent(parentNode);
                }}
            }};
            navRight.onclick = () => {{
                if (currentNode && currentNode.children && currentNode.children.length > 0) {{
                    const firstChildWithText = currentNode.children.find(c => c.at.length > 0);
                    if (firstChildWithText) renderContent(firstChildWithText);
                }}
            }};

            // 5. Image Side
            const imgDiv = document.createElement('div');
            imgDiv.style.flex = '3';
            imgDiv.style.position = 'relative';
            imgDiv.style.borderLeft = '1px solid #333';
            imgDiv.style.boxSizing = 'border-box';
            imgDiv.style.overflow = 'hidden';

            if (RANDOM_TEXTDIV_POSITION) {{
                const seed = child.path.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * SEED;
                const rand = seededRandom(seed);
                if (rand < 0.5) {{ div.appendChild(textWrapper); div.appendChild(imgDiv); }}
                else {{ div.appendChild(imgDiv); div.appendChild(textWrapper); }}
            }} else {{
                 div.appendChild(textWrapper); div.appendChild(imgDiv);
            }}
            
            div._sceneContainer = imgDiv;
            div._sceneChild = child;


        }} else if (child.ai.length > 0) {{
            div._sceneContainer = div;
            div._sceneChild = child;
       }} else if (child.at.length > 0) {{
            div.className = 'content-div';
            div.style.position = 'relative';
            div.style.overflow = 'hidden';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.width = '100%';
            textDiv.style.height = '100%';
            textDiv.style.overflowY = 'auto';
            textDiv.style.position = 'absolute';
            textDiv.style.top = '0';
            textDiv.style.left = '0';
            
            let htmlContent = '';
            for (const path of child.at) {{ htmlContent += await loadText(path); }}
            textDiv.innerHTML = htmlContent;
            
            const scriptTags = textDiv.querySelectorAll('script');
            scriptTags.forEach(oldScript => {{
                const newScript = document.createElement('script');
                newScript.textContent = oldScript.textContent;
                oldScript.parentNode.replaceChild(newScript, oldScript);
            }});
            
            const pathParts = child.path.split('/');
            const labelHtml = pathParts.map((part, idx) => {{
                const partPath = pathParts.slice(0, idx + 1).join('/');
                let color = 'white';
                if (currentNode && partPath === currentNode.path) {{
                    color = '#44f';
                }}
                
                const pNode = findNodeByPath(dataTree, partPath);
                const dot = (pNode && pNode.na) ? '<span style="color:#f44;font-size:9px;vertical-align:middle;margin-left:1px;">●</span>' : '';
                
                return `<span style="color:${{color}};cursor:pointer" data-path="${{partPath}}">${{part}}${{dot}}</span>`;
            }}).join('/');
            
            const labelDiv = document.createElement('div');
            labelDiv.className = 'div-label';
            labelDiv.innerHTML = labelHtml;
            labelDiv.querySelectorAll('span[data-path]').forEach(span => {{
                span.onclick = (e) => {{
                    e.stopPropagation();
                    const node = findNodeByPath(dataTree, span.dataset.path);
                    if (node) renderContent(node);
                }};
            }});
            
            const navDiv = document.createElement('div');
            navDiv.innerHTML = `<span style="cursor:pointer;padding:0 5px;user-select:none;color:#ffff" class="text-nav-left">&#60;</span><span style="padding:0 2px">texts</span><span style="cursor:pointer;padding:0 5px;user-select:none;color:#ffffff" class="text-nav-right">&#62;</span>`;
            navDiv.style.cssText = 'position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;padding:2px 5px;z-index:100';
            
            const navLeft = navDiv.querySelector('.text-nav-left');
            const navRight = navDiv.querySelector('.text-nav-right');
            navLeft.onclick = () => {{
                if (currentNode && currentNode.path) {{
                    const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                    const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                    if (parentNode && parentNode.at.length > 0) renderContent(parentNode);
                }}
            }};
            navRight.onclick = () => {{
                if (currentNode && currentNode.children && currentNode.children.length > 0) {{
                    const firstChildWithText = currentNode.children.find(c => c.at.length > 0);
                    if (firstChildWithText) renderContent(firstChildWithText);
                }}
            }};
            
            div.appendChild(textDiv);
            div.appendChild(labelDiv);
            div.appendChild(navDiv);
        }}
        contentDiv.appendChild(div);
    }}

    await new Promise(resolve => requestAnimationFrame(resolve));
    const sceneDivs = Array.from(contentDiv.children).filter(d => d._sceneContainer);
    for (const div of sceneDivs) {{
        scenePromises.push(createThreeScene(div._sceneContainer, div._sceneChild.ai, div._sceneChild));
    }}
    await Promise.all(scenePromises);
    return Promise.resolve();
}}
</script>
</body>
</html>''')









print("Generated spritesheets, data.json and index.html")