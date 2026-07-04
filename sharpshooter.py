import pygame,random,math,struct,sys,os,subprocess,json,urllib.request,urllib.error

if __name__ == "__main__" and not os.environ.get("SHAPE_SHOOTER_FROM_LAUNCHER"):
    _launch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch.py")
    sys.exit(subprocess.call([sys.executable, _launch]))

pygame.init()
pygame.font.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def make_beep(freq, duration_ms, volume=0.25, decay=0.5):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    frames = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        envelope = max(0, 1 - (i / n_samples) ** decay)
        sample = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * t))
        sample = max(-32767, min(32767, sample))
        frames += struct.pack('<hh', sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))

def make_death_sound():
    sample_rate = 44100
    duration_ms = 450
    n_samples = int(sample_rate * duration_ms / 1000)
    frames = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = 220 - 120 * progress
        envelope = max(0, 1 - progress ** 0.7)
        sample = int(32767 * 0.35 * envelope * math.sin(2 * math.pi * freq * t))
        sample = max(-32767, min(32767, sample))
        frames += struct.pack('<hh', sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))

def make_wave_sound():
    sample_rate = 44100
    frames = bytearray()
    for freq, duration_ms in [(523, 90), (659, 90), (784, 140)]:
        n_samples = int(sample_rate * duration_ms / 1000)
        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0, 1 - (i / n_samples) ** 0.4)
            sample = int(32767 * 0.22 * envelope * math.sin(2 * math.pi * freq * t))
            sample = max(-32767, min(32767, sample))
            frames += struct.pack('<hh', sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))

SOUNDS = {
    "shoot": make_beep(920, 55, 0.18, 0.8),
    "hit": make_beep(420, 90, 0.22, 0.6),
    "death": make_death_sound(),
    "wave": make_wave_sound(),
}

def play_sound(name):
    sound = SOUNDS.get(name)
    if sound:
        sound.play()

#Checks if the game should be quit
def checkQuit(events):
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
            exit()


def hoverrect(rectx,recty,rectwidth,rectlen,rectcolour,text,textcolour,textsize,mousex,mousey,event1):
    displayRect([rectx,recty,rectwidth,rectlen],rectcolour,center=True)
    if (rectx-(0.5*rectwidth))<=mousex<=(rectx+(0.5*rectwidth)) and (recty-(0.5*rectlen))<=mousey<=(recty+(0.5*rectlen)):
        rectcolour = (255-rectcolour[0],255-rectcolour[1],255-rectcolour[2])
        textcolour = (255-textcolour[0],255-textcolour[1],255-textcolour[2])

        for event in events:
            if event.type==pygame.MOUSEBUTTONDOWN:
                event1 = not(event1)
    displayRect([rectx,recty,rectwidth,rectlen],rectcolour,center=True), displayMessage(text,[rectx,recty],colour=textcolour,size=textsize,center=True)
    return event1

def invisirect(rectx,recty,rectwidth,rectlen,rectcolour,text,textcolour,textsize,mousex,mousey,event1,colourchange=(0,0,0)):
    displayRect([rectx,recty,rectwidth,rectlen],rectcolour,center=True)
    if (rectx-(0.5*rectwidth))<=mousex<=(rectx+(0.5*rectwidth)) and (recty-(0.5*rectlen))<=mousey<=(recty+(0.5*rectlen)):
        textcolour = colourchange

        for event in events:
            if event.type==pygame.MOUSEBUTTONDOWN:
                event1 = not(event1)
    displayRect([rectx,recty,rectwidth,rectlen],rectcolour,center=True), displayMessage(text,[rectx,recty],colour=textcolour,size=textsize,center=True)
    return event1
#dimensions - e.g. [50,50] - the x and y co-ordinates of the circule you want to draw
#radius - e.g. 40 - the radius of the circle
#colour - e.g. "white" - the colour of the circle 
def displayCircle(dimensions,radius,colour):
    return pygame.draw.circle(dis,colour,dimensions,radius)

def circles_overlap(x1, y1, r1, x2, y2, r2, padding=0):
    dx = x1 - x2
    dy = y1 - y2
    reach = r1 + r2 + padding
    return dx * dx + dy * dy <= reach * reach


def enemy_bullet_hit_radius():
    return max(enemysize - ENEMY_BULLET_HIT_INSET, 1)


def player_touched_by_enemy(enemy_x, enemy_y):
    return circles_overlap(youX, youY, PLAYER_HIT_RADIUS, enemy_x, enemy_y, enemysize, 0)


def draw_debug_hitboxes():
    if not DEBUG_HITBOXES:
        return
    pygame.draw.circle(dis, (0, 255, 255), (int(youX), int(youY)), PLAYER_HIT_RADIUS, 1)
    enemy_hit_r = enemy_bullet_hit_radius()
    for enemy in enemies:
        ex, ey = int(enemy[0]), int(enemy[1])
        pygame.draw.circle(dis, (255, 0, 0), (ex, ey), enemysize, 1)
        pygame.draw.circle(dis, (255, 255, 0), (ex, ey), enemy_hit_r, 1)

#dimentions - e.g. [0,0,40,40] - The x,y and width,height of the rectangle
#colour - e.g. "white" - The background colour of the rectangle
#(optional)center - e.g. True - Whether the recentagle should be centered around the x,y co-ordinates
def displayRect(dimensions, colour,center=False):
    location = dimensions[:]
    if center:
        location[0] -= location[2]//2
        location[1] -= location[3]//2
    return pygame.draw.rect(dis,colour,location)

#msg - e.g. "this is a message" - the message you wish to display
#loc - e.g. [50,50] - the x and y co-ordinates of the image you want to display
#(optional)colour - e.g. "white" - the colour of the text
#(optional)size - e.g. 30 - The size of the text
#(optional)center - e.g. True - If you want the image to be centered around the location or not
def displayMessage(msg,loc,colour="black",size=25,center=False):
    comicSans = pygame.freetype.SysFont('Consolas', size)
    text_surface,rect = comicSans.render(msg,colour)
    
    if center:
        text_rect = text_surface.get_rect(center=loc)
        return dis.blit(text_surface,text_rect)
    else:
        text_rect = text_surface.get_rect(topleft=loc)
        return dis.blit(text_surface, text_rect)

def text_on_background(size=25):
    return (255-background[0], 255-background[1], 255-background[2])

def draw_overlay(title, subtitle=None, center_x=None, center_y=None):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    dis.blit(overlay, (0, 0))
    cx = SCREEN_WIDTH/2 if center_x is None else center_x
    cy = SCREEN_HEIGHT/2 - 25 if center_y is None else center_y
    displayMessage(title, [cx, cy], (255, 255, 255), 44, True)
    if subtitle:
        displayMessage(subtitle, [cx, cy + 50], (210, 210, 210), 18, True)

def panel_colour():
    return (max(0, background[0] - 20), max(0, background[1] - 20), max(0, background[2] - 20))

def intermission_right_center():
    return UPGRADE_PANEL_WIDTH + (SCREEN_WIDTH - UPGRADE_PANEL_WIDTH) // 2

def draw_hud_bar(enemy_count):
    bar_colour = (max(0, background[0] - 35), max(0, background[1] - 35), max(0, background[2] - 35))
    displayRect([0, 0, SCREEN_WIDTH, 40], bar_colour)
    displayRect([0, 39, SCREEN_WIDTH, 1], (0, 210, 150))
    fg = text_on_background()
    displayMessage("Wave " + str(wave), [SCREEN_WIDTH/2, 20], fg, 18, True)
    displayMessage("Enemies: " + str(enemy_count), [SCREEN_WIDTH - 80, 20], fg, 16, True)

def draw_reload_bar(cooldown, max_cooldown):
    if max_cooldown <= 0:
        return
    fg = text_on_background()
    displayMessage("Reload", [55, SCREEN_HEIGHT - 28], fg, 14, True)
    displayRect([20, SCREEN_HEIGHT - 18, 120, 10], (80, 80, 80))
    fill = max(0, int(120 * (1 - cooldown / max_cooldown)))
    if fill > 0:
        displayRect([20, SCREEN_HEIGHT - 18, fill, 10], (0, 210, 150))

def draw_color_swatch(cx, cy, colour):
    displayCircle([cx, cy], 11, (80, 80, 80))
    displayCircle([cx, cy], 9, colour)
    pygame.draw.circle(dis, (80, 80, 80), (int(cx), int(cy)), 9, 1)

def draw_death_flash(timer):
    if timer <= 0:
        return
    intensity = min(200, 80 + timer * 8)
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((255, 40, 40, intensity))
    dis.blit(overlay, (0, 0))

def wrap_text_lines(text, font, max_width):
    """Split text into lines that fit within max_width pixels."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word]) if current else word
        if font.get_rect(candidate).width <= max_width:
            current.append(word)
            continue
        if current:
            lines.append(" ".join(current))
            current = []
        if font.get_rect(word).width <= max_width:
            current = [word]
            continue
        chunk = ""
        for ch in word:
            trial = chunk + ch
            if font.get_rect(trial).width <= max_width:
                chunk = trial
            else:
                if chunk:
                    lines.append(chunk)
                chunk = ch
        if chunk:
            current = [chunk]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_wrapped_text(text, y, colour, size, max_width, align="center", line_gap=None):
    """Render wrapped text; returns y position below the last line."""
    font = pygame.freetype.SysFont("Consolas", size)
    if line_gap is None:
        line_gap = size + 5
    lines = wrap_text_lines(text, font, max_width)
    left_x = (SCREEN_WIDTH - max_width) // 2
    for line in lines:
        surface, _ = font.render(line, colour)
        if align == "center":
            rect = surface.get_rect(midtop=(SCREEN_WIDTH // 2, int(y)))
        else:
            rect = surface.get_rect(topleft=(left_x, int(y)))
        dis.blit(surface, rect)
        y += line_gap
    return y


def _wrapped_block_height(text, size, max_width, line_gap):
    font = pygame.freetype.SysFont("Consolas", size)
    return len(wrap_text_lines(text, font, max_width)) * line_gap


def draw_revision_screen(question, feedback=None, quiz_index=0, quiz_total=5, quiz_score=0, pass_score=4):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    dis.blit(overlay, (0, 0))
    fg = (255, 255, 255)
    hint_y = SCREEN_HEIGHT - 40
    max_width = int(SCREEN_WIDTH * 0.85)

    displayMessage("Revision Quiz", [SCREEN_WIDTH / 2, 36], fg, 26, True)
    displayMessage(f"Question {quiz_index + 1}/{quiz_total}", [SCREEN_WIDTH / 2, 62], (200, 220, 255), 16, True)
    displayMessage(f"Score: {quiz_score}/{quiz_total}", [SCREEN_WIDTH / 2, 82], (180, 255, 200), 16, True)

    if feedback == "fail":
        fail_text = f"You scored {quiz_score}/{quiz_total}. You need {pass_score}/{quiz_total} to pass."
        draw_wrapped_text(fail_text, 220, (255, 120, 120), 20, max_width, "center", 26)
        return

    content_top = 108

    q_size, opt_size = 18, 16
    q_gap, opt_gap = q_size + 5, opt_size + 4
    available = hint_y - content_top - (50 if feedback else 28)

    def total_content_height():
        height = _wrapped_block_height(question["question"], q_size, max_width, q_gap) + 14
        for i, opt in enumerate(question["options"]):
            line = f"{i + 1}. {opt}"
            height += _wrapped_block_height(line, opt_size, max_width, opt_gap) + 6
        return height

    while total_content_height() > available and (q_size > 14 or opt_size > 13):
        if opt_size > 13:
            opt_size -= 1
            opt_gap = opt_size + 3
        elif q_size > 14:
            q_size -= 1
            q_gap = q_size + 4

    y = draw_wrapped_text(question["question"], content_top, fg, q_size, max_width, "center", q_gap)
    y += 14
    for i, opt in enumerate(question["options"]):
        line = f"{i + 1}. {opt}"
        y = draw_wrapped_text(line, y, fg, opt_size, max_width, "left", opt_gap)
        y += 6

    if feedback == "correct":
        displayMessage("Correct!", [SCREEN_WIDTH / 2, min(y + 20, hint_y - 50)], (120, 255, 180), 32, True)
    elif feedback == "wrong":
        ci = question["correct"]
        wrong_text = f"Wrong — the correct answer was {ci + 1}. {question['options'][ci]}"
        draw_wrapped_text(wrong_text, min(y + 10, hint_y - 80), (255, 120, 120), 16, max_width, "center", 21)
    else:
        displayMessage("Press 1-4 to answer", [SCREEN_WIDTH / 2, hint_y], (200, 200, 200), 14, True)

def shuffle_question_options(question, q_num=None):
    """Shuffle MCQ options and update correct index to match."""
    q = dict(question)
    options = q["options"][:]
    correct_answer = options[int(q["correct"])]
    random.shuffle(options)
    q["options"] = options
    q["correct"] = options.index(correct_answer)
    labels = ["A", "B", "C", "D"]
    prefix = f"Q{q_num} " if q_num is not None else ""
    print(f"[REVISION DEBUG] {prefix}correct answer: {labels[q['correct']]} (index {q['correct']})")
    return q


def fetch_revision_quiz(count=5):
    port = os.getenv("STUDY_CHAT_PORT", "8765")
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/revision-quiz?count={count}", timeout=120
        ) as resp:
            data = json.loads(resp.read().decode())
            questions = data.get("questions", [])
            valid = [
                q for q in questions
                if q.get("question") and len(q.get("options", [])) == 4 and 0 <= int(q.get("correct", -1)) <= 3
            ]
            if len(valid) == count:
                print(
                    "[REVISION DEBUG] game received quiz | source:",
                    data.get("source", "gemini"),
                    "| questions:",
                    len(valid),
                )
                for i, q in enumerate(valid):
                    print(f"[REVISION DEBUG]   Q{i + 1}:", repr(q.get("question")))
                return [shuffle_question_options(q, i + 1) for i, q in enumerate(valid)]
            print("[REVISION DEBUG] quiz API returned invalid question count:", len(valid), "expected", count)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"[REVISION DEBUG] quiz API HTTP {exc.code}: {body}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        print(f"[REVISION DEBUG] quiz API request failed: {exc}")
    print("[REVISION DEBUG] using 5 FALLBACK questions (hardcoded)")
    return [shuffle_question_options(q.copy(), i + 1) for i, q in enumerate(FALLBACK_REVISIONS)]


def fetch_revision_question():
    port = os.getenv("STUDY_CHAT_PORT", "8765")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/revision-question", timeout=20) as resp:
            data = json.loads(resp.read().decode())
            if len(data.get("options", [])) == 4 and 0 <= int(data.get("correct", -1)) <= 3:
                print(
                    "[REVISION DEBUG] game received | source:",
                    data.get("source", "gemini"),
                    "| question:",
                    repr(data.get("question")),
                )
                return data
            print("[REVISION DEBUG] API response missing valid question/options:", data)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"[REVISION DEBUG] API HTTP {exc.code}: {body}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        print(f"[REVISION DEBUG] API request failed: {exc}")
    print("[REVISION DEBUG] using FALLBACK question (hardcoded ALU)")
    return None

def revision_answer_index(key):
    pairs = [
        (pygame.K_1, 0),
        (pygame.K_2, 1),
        (pygame.K_3, 2),
        (pygame.K_4, 3),
    ]
    for k, idx in pairs:
        if key == k:
            return idx
    return None

#imageSrc - e.g. "Pea.png" - The name of the image inside the images folder
def loadImage(imageSrc):
    return pygame.image.load("./images/" + imageSrc)

#imageObj - e.g. img_variable - The value returned from the loadImage() function
#loc - e.g. [40,50] - the x and y co-ordinates of the image
#(optional)scale - e.g. 0.5 - how much you want to scale the image by with 1 being original size
#(optional)center - e.g. False - Centers the sprite around the x and y instead of the top left
def displayImage(imageVar,loc,scale=1,center=False):
    size = imageVar.get_size()
    width = size[0] * scale
    height = size[1] * scale
    imp = pygame.transform.scale(imageVar, (width,height))
    coord = loc[:]
    if center:
        coord[0] -= width//2 
        coord[1] -= height//2
    return dis.blit(imp, coord)

#Initiate pygame
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
UPGRADE_PANEL_WIDTH = 380
UPGRADE_ROW_START = 92
UPGRADE_ROW_HEIGHT = 64
UPGRADE_LABEL_X = 22
UPGRADE_PIP_X = 208
UPGRADE_PIP_GAP = 14
UPGRADE_PIP_STEP = 17
INTERMISSION_PANEL = (205, 208, 215)
EMPTY_PIP = (130, 130, 130)
fullscreen = False
dis=pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
pygame.display.set_caption("Shape Shooter")
clock = pygame.time.Clock()

upgrades = {"Max Speed":0,"Acceleration":0,"Reload Rate":0,"Bullet Speed":0,"Piercing Bullet":0,"Bullet Size":0,"Ricochet":0}
trueUpgrades = {"Max Speed":0,"Acceleration":0,"Reload Rate":0,"Bullet Speed":0,"Piercing Bullet":0,"Bullet Size":0,"Ricochet":0}
upmaxes = [4,5,6,3,1,4,4]

youX = 400
youY = 100
cubecolour = (0,0,0)

Xacc = 0
Yacc = 0 
accincrease = 0.2

bullets = []
bullet_speed = 2
cooldown = 0

enemies = []
enemyamount = 10
enemyspeed = 1
eneymymax = 10
spawnrate = 30
enemysize = 10
ENEMY_HIT_PADDING = 0
ENEMY_BULLET_HIT_INSET = 1
PLAYER_HIT_RADIUS = 12
DEBUG_HITBOXES = False
FALLBACK_REVISIONS = [
    {
        "question": "In A-level Computer Science, what is the main function of the ALU?",
        "options": ["Long-term storage", "Arithmetic and logic operations", "Network routing", "Display output"],
        "correct": 1,
    },
    {
        "question": "Which component temporarily holds data and instructions the CPU is currently using?",
        "options": ["Hard disk", "RAM", "Optical drive", "Power supply"],
        "correct": 1,
    },
    {
        "question": "In the fetch-decode-execute cycle, what happens during the decode stage?",
        "options": [
            "The instruction is carried out",
            "The instruction is copied from memory to the CPU",
            "The CPU interprets the instruction",
            "The program is saved to storage",
        ],
        "correct": 2,
    },
    {
        "question": "How many bits are in one byte?",
        "options": ["4", "8", "16", "32"],
        "correct": 1,
    },
    {
        "question": "Which of these is an example of secondary storage?",
        "options": ["Cache", "Register", "SSD", "Control unit"],
        "correct": 2,
    },
]
REVISION_QUIZ_TOTAL = 5
REVISION_QUIZ_PASS = 4
REVISION_FEEDBACK_FRAMES = 90

circleinput = []
choosecolour = False
enterpressed = False
cubechange = False
changeback = False

count = 0

pregame = True
roundactive = False

paused = False
wave = 1
credits = 3
player_died = False
dying = False
death_flash_timer = 0
nextText = "Start Wave 1"
max_cooldown = 60
revision_active = False
revision_quiz_questions = []
revision_quiz_index = 0
revision_quiz_score = 0
revision_question = None
revision_feedback = None
revision_feedback_timer = 0

background = (255,255,255)

while True:
    count+=1
    events = pygame.event.get()
    held_down=pygame.key.get_pressed()
    mouse_x,mouse_y = pygame.mouse.get_pos() 
    checkQuit(events)
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            fullscreen = not fullscreen
            if fullscreen:
                dis = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                dis = pygame.display.set_mode((800, 600))
            SCREEN_WIDTH, SCREEN_HEIGHT = dis.get_size()
    dis.fill((background))

    if pregame:
        displayRect([youX,youY,20,20],(0,0,0),center=True)
        if youX>0:
            if (held_down[pygame.K_LEFT] or held_down[pygame.K_a]):
                youX-=Xacc
        if youX<SCREEN_WIDTH:
            if (held_down[pygame.K_RIGHT] or held_down[pygame.K_d]):
                youX+=Xacc
        if 0<youY:
            if (held_down[pygame.K_UP] or held_down[pygame.K_w]):
                youY-=Yacc
        if youY<SCREEN_HEIGHT:
            if (held_down[pygame.K_DOWN] or held_down[pygame.K_s]):
                youY+=Yacc
        if (held_down[pygame.K_LEFT] or held_down[pygame.K_a] or held_down[pygame.K_RIGHT] or held_down[pygame.K_d]):
            if Xacc<5:
                Xacc+=accincrease
        else:
            Xacc=0
        if held_down[pygame.K_UP] or held_down[pygame.K_w] or held_down[pygame.K_DOWN] or held_down[pygame.K_s]:
            if Yacc<5:
                Yacc+=accincrease
        else:
            Yacc=0
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if cooldown==0:
                    cooldown = 60 

                    dx = mouse_x - youX
                    dy = mouse_y - youY
                    distance = math.sqrt(dx**2 + dy**2)                
                    if distance != 0: 
                        dx = dx / distance
                        dy = dy / distance
                    
                    bullets.append({
                        "bulletX": youX,
                        "bulletY": youY,
                        "velocityX": dx * bullet_speed,
                        "velocityY": dy * bullet_speed
                    })
                    play_sound("shoot")
        for bullet in bullets[:]:
            bullet["bulletX"] += bullet["velocityX"]
            bullet["bulletY"] += bullet["velocityY"]
            tsbullet = displayCircle([bullet["bulletX"], bullet["bulletY"]], 3, (0, 0, 0))
            for enemy in enemies[:]:
                if circles_overlap(bullet["bulletX"], bullet["bulletY"], 3, enemy[0], enemy[1], enemy_bullet_hit_radius(), ENEMY_HIT_PADDING):
                    enemies.remove(enemy)
                    bullets.remove(bullet)
                    break
            if bullet in bullets and (bullet["bulletX"]>SCREEN_WIDTH or bullet["bulletX"]<0 or bullet["bulletY"]>SCREEN_HEIGHT or bullet["bulletY"]<0):
                bullets.remove(bullet)
        if cooldown>0:
            draw_reload_bar(cooldown, 60)
            cooldown-=1

        displayMessage("Shape Shooter", [SCREEN_WIDTH/2, 120], (0, 0, 0), 52, True)
        displayMessage("WASD move  ·  Mouse aim & shoot  ·  P pause  ·  F11 fullscreen", [SCREEN_WIDTH/2, 175], (80, 80, 80), 16, True)
        displayMessage("Try shooting before you start", [SCREEN_WIDTH/2, 520], (120, 120, 120), 14, True)

        pregame = hoverrect(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 40, 160, 55, (0, 210, 150), "START", (255, 255, 255), 28, mouse_x, mouse_y, pregame)
        if not(pregame):
            roundactive = True
            player_died = False
            dying = False
            death_flash_timer = 0
            paused = False
            nextText = "Wave " + str(wave)
            youX = 400
            youY = 300

            Xacc = 0
            Yacc = 0 
            accincrease = 0.2

            bullets = []
            bullet_speed = 2
            cooldown = 0

            enemies = []
            enemyamount = 10
            enemyspeed = 1

            count = 0
            events = []
    if roundactive:
        for event in events:
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_p and not dying:
                    paused = not paused
        player_colour = (255, 60, 60) if dying and (death_flash_timer // 3) % 2 == 0 else cubecolour
        displayRect([youX,youY,20,20], player_colour, center=True)
        if not(paused) and not(dying):
            if youX>0:
                if (held_down[pygame.K_LEFT] or held_down[pygame.K_a]):
                    youX-=Xacc
            if youX<SCREEN_WIDTH:
                if (held_down[pygame.K_RIGHT] or held_down[pygame.K_d]):
                    youX+=Xacc
            if 0<youY:
                if (held_down[pygame.K_UP] or held_down[pygame.K_w]):
                    youY-=Yacc
            if youY<SCREEN_HEIGHT:
                if (held_down[pygame.K_DOWN] or held_down[pygame.K_s]):
                    youY+=Yacc

        #acceleration
            if (held_down[pygame.K_LEFT] or held_down[pygame.K_a] or held_down[pygame.K_RIGHT] or held_down[pygame.K_d]):
                if Xacc<(5+trueUpgrades["Max Speed"]):
                    Xacc+=accincrease
            else:
                Xacc=0
            if held_down[pygame.K_UP] or held_down[pygame.K_w] or held_down[pygame.K_DOWN] or held_down[pygame.K_s]:
                if Yacc<(5+trueUpgrades["Max Speed"]):
                    Yacc+=accincrease
            else:
                Yacc=0

        #shooting
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if cooldown==0:
                        cooldown = 60 - (10*trueUpgrades["Reload Rate"])
                        max_cooldown = cooldown

                        dx = mouse_x - youX
                        dy = mouse_y - youY
                        
                        distance = math.sqrt(dx**2 + dy**2)
                    
                        if distance != 0: 
                            dx = dx / distance
                            dy = dy / distance
                        
                        bullets.append({
                            "bulletX": youX,
                            "bulletY": youY,
                            "velocityX": dx * bullet_speed,
                            "velocityY": dy * bullet_speed,
                            "Bounces":0
                        })
                        play_sound("shoot")

        for bullet in bullets[:]:
            if not(paused) and not(dying):
                bullet["bulletX"] += bullet["velocityX"]
                bullet["bulletY"] += bullet["velocityY"]
            bullet_radius = 3 + trueUpgrades["Bullet Size"]
            tsbullet = displayCircle([bullet["bulletX"], bullet["bulletY"]], bullet_radius, (255-background[0],255-background[1],255-background[2]))
            for enemy in enemies[:]:
                if circles_overlap(bullet["bulletX"], bullet["bulletY"], bullet_radius, enemy[0], enemy[1], enemy_bullet_hit_radius(), ENEMY_HIT_PADDING):
                    enemies.remove(enemy)
                    play_sound("hit")
                    if trueUpgrades["Piercing Bullet"]<1:
                        bullets.remove(bullet)
                    break
            if bullet not in bullets:
                continue
            if trueUpgrades["Ricochet"]==0:
                if (bullet["bulletX"]>SCREEN_WIDTH or bullet["bulletX"]<0 or bullet["bulletY"]>SCREEN_HEIGHT or bullet["bulletY"]<0):
                    bullets.remove(bullet)
            else:
                if (bullet["bulletX"]>SCREEN_WIDTH or bullet["bulletX"]<0):
                    bullet["velocityX"] *= -1
                    bullet["Bounces"]+=1
                if (bullet["bulletY"]>SCREEN_HEIGHT or bullet["bulletY"]<0):
                    bullet["velocityY"] *= -1
                    bullet["Bounces"]+=1
                if bullet["Bounces"]>trueUpgrades["Ricochet"]:
                    bullets.remove(bullet)
            

        if cooldown>0:
            draw_reload_bar(cooldown, max_cooldown)
            if not(paused) and not(dying):
                cooldown-=1


        if not paused and not dying:
        #spawning + displaying enemies
            if enemyamount>0:
                if count%spawnrate==0:
                    enemyamount-=1
                    inorout = random.randint(0,1)
                    upordown = random.randint(0,1)
                    if upordown == 1:
                        if inorout==0:
                            enemyX = random.randint(-10,0)
                        else:
                            enemyX = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 10)
                        enemyY = random.randint(-10, SCREEN_HEIGHT + 10)
                    else:
                        if inorout==1:
                            enemyY = random.randint(-10,0)
                        else:
                            enemyY = random.randint(SCREEN_HEIGHT, SCREEN_HEIGHT + 10)
                        enemyX = random.randint(-10, SCREEN_WIDTH + 10)
                    enemies.append([enemyX,enemyY])

        for enemy in enemies:
            if not(paused) and not(dying):
                distanceX = (youX - enemy[0])
                distanceY = (youY-enemy[1])
                distanceT = math.sqrt(distanceX**2 + distanceY**2)
                if distanceT!=0:
                    distanceX /= distanceT
                    distanceY /= distanceT
                enemy[0]+=distanceX*enemyspeed
                enemy[1]+=distanceY*enemyspeed
            tsenemy = displayCircle([enemy[0],enemy[1]],enemysize,(255,0,0))
            if player_touched_by_enemy(enemy[0], enemy[1]) and not dying:
                dying = True
                death_flash_timer = 21
                play_sound("death")
        if not dying and len(enemies) == 0 and enemyamount==0 and roundactive:
            roundactive = False
            revision_active = True
            revision_quiz_questions = fetch_revision_quiz(REVISION_QUIZ_TOTAL)
            revision_quiz_index = 0
            revision_quiz_score = 0
            revision_question = revision_quiz_questions[0]
            revision_feedback = None
            revision_feedback_timer = 0
            play_sound("wave")
        draw_hud_bar(len(enemies))
        draw_debug_hitboxes()
        if dying:
            death_flash_timer -= 1
            draw_death_flash(death_flash_timer)
            if death_flash_timer <= 0:
                roundactive = False
                player_died = True
                dying = False
                nextText = "Try Again"
        elif paused:
            draw_overlay("PAUSED", "Press P to resume")

    if revision_active and revision_question:
        if revision_feedback_timer > 0:
            revision_feedback_timer -= 1
            if revision_feedback_timer == 0:
                if revision_feedback in ("correct", "wrong"):
                    if revision_quiz_index < REVISION_QUIZ_TOTAL - 1:
                        revision_quiz_index += 1
                        revision_question = revision_quiz_questions[revision_quiz_index]
                        revision_feedback = None
                    elif revision_quiz_score >= REVISION_QUIZ_PASS:
                        player_died = False
                        nextText = "Wave " + str(wave + 1)
                        revision_active = False
                        revision_quiz_questions = []
                        revision_quiz_index = 0
                        revision_quiz_score = 0
                        revision_question = None
                        revision_feedback = None
                    else:
                        revision_feedback = "fail"
                        revision_feedback_timer = REVISION_FEEDBACK_FRAMES * 2
                elif revision_feedback == "fail":
                    revision_active = False
                    revision_quiz_questions = []
                    revision_quiz_index = 0
                    revision_quiz_score = 0
                    revision_question = None
                    revision_feedback = None
                    roundactive = True
                    youX = 400
                    youY = 300
                    Xacc = 0
                    Yacc = 0
                    bullets = []
                    enemies = []
                    enemyamount = eneymymax
                    count = 0
                    cooldown = 0
                    paused = False
        elif revision_feedback is None:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    choice = revision_answer_index(event.key)
                    if choice is not None:
                        if choice == revision_question["correct"]:
                            revision_quiz_score += 1
                            revision_feedback = "correct"
                        else:
                            revision_feedback = "wrong"
                        revision_feedback_timer = REVISION_FEEDBACK_FRAMES
                        break
        if revision_active:
            draw_revision_screen(
                revision_question,
                revision_feedback,
                revision_quiz_index,
                REVISION_QUIZ_TOTAL,
                revision_quiz_score,
                REVISION_QUIZ_PASS,
            )

    if not(roundactive) and not(pregame) and not(revision_active):
           fg = text_on_background()
           panel_bg = panel_colour()
           right_x = UPGRADE_PANEL_WIDTH + 2
           right_center = intermission_right_center()

           displayRect([0, 0, UPGRADE_PANEL_WIDTH, SCREEN_HEIGHT], panel_bg)
           displayRect([right_x, 0, SCREEN_WIDTH - right_x, SCREEN_HEIGHT], INTERMISSION_PANEL)
           displayRect([UPGRADE_PANEL_WIDTH, 0, 2, SCREEN_HEIGHT], (0, 210, 150))

           displayMessage("Upgrades", [UPGRADE_PANEL_WIDTH // 2, 38], fg, 26, True)

           if player_died:
               displayMessage("YOU DIED", [right_center, 130], (200, 40, 40), 44, True)
               displayMessage("Spend upgrades or try again", [right_center, 185], (50, 50, 50), 18, True)
           else:
               displayMessage("WAVE CLEARED", [right_center, 130], (0, 140, 90), 40, True)
               displayMessage("Wave " + str(wave) + " complete", [right_center, 185], (50, 50, 50), 18, True)

           draw_color_swatch(right_center - 60, 300, background)
           changebackground = displayCircle([right_center - 60, 300], 9, (background))
           draw_color_swatch(right_center + 60, 300, cubecolour)
           changecube = displayCircle([right_center + 60, 300], 9, (cubecolour))
           displayMessage("BG", [right_center - 60, 330], (50, 50, 50), 12, True)
           displayMessage("You", [right_center + 60, 330], (50, 50, 50), 12, True)
           counter = 0
           upgradeselected = False
           nextround = False
           numtotal = 0
           maxout = False
           for num in upmaxes:
                numtotal+=num
           if credits>0:
            displayMessage("Points: " + str(credits), [right_center, 55], (50, 50, 50), 22, True)
           nextround = hoverrect(right_center, 240, 200, 75, (50, 50, 175), nextText, (255, 255, 255), 25, mouse_x, mouse_y, nextround)
           if nextround:
               if not player_died:
                   if wave>=5:
                       if enemysize>3:
                           enemysize-=0.5
                   eneymymax+=1
                   wave+=1
                   if enemyspeed<8.8:
                       enemyspeed+=0.1
                   numtotal = 0
                   for num in upmaxes:
                       numtotal+=num
                   if (wave)<=(numtotal+1):
                       credits+=1
                   nextText = "Wave " + str(wave)
               roundactive = True
               nextround = False
               player_died = False
               dying = False
               death_flash_timer = 0
               paused = False
               youX = 400
               youY = 300

               Xacc = 0
               Yacc = 0 
               accincrease = 0.2+(0.2*trueUpgrades["Acceleration"])

               bullets = []
               bullet_speed = 2 + (2*trueUpgrades["Bullet Speed"])
               cooldown = 0

               enemies = []
               enemyamount = eneymymax

               count = 0
               events = []
               choosecolour = False
               changeback = False
               cubechange = False
           for tsupgrade in upgrades:
               row_y = UPGRADE_ROW_START + UPGRADE_ROW_HEIGHT * counter
               label_width = UPGRADE_PIP_X - UPGRADE_PIP_GAP - UPGRADE_LABEL_X
               label_rect = pygame.Rect(UPGRADE_LABEL_X, row_y - 12, label_width, 24)
               label_hover = label_rect.collidepoint(mouse_x, mouse_y)
               label_colour = (255, 0, 0) if label_hover else fg
               displayMessage(tsupgrade, [UPGRADE_LABEL_X, row_y - 8], label_colour, 16, center=False)
               for event in events:
                   if event.type == pygame.MOUSEBUTTONDOWN and label_hover:
                       upgradeselected = True
               if upgrades[tsupgrade]>0:
                maxout = invisirect(UPGRADE_PANEL_WIDTH - 32, row_y, 48, 26, panel_bg, "MAX", fg, 11, mouse_x, mouse_y, maxout, colourchange=(0, 255, 0))
               sepcount = 0

               for g in range(upmaxes[counter]):
                   displayRect([UPGRADE_PIP_X + (UPGRADE_PIP_STEP * sepcount), row_y, 14, 14], EMPTY_PIP, center=True)
                   sepcount+=1
               sepcount = 0
               for h in range(trueUpgrades[tsupgrade]):
                    displayRect([UPGRADE_PIP_X + (UPGRADE_PIP_STEP * sepcount), row_y, 12, 12], (0, 200, 80), center=True)
                    sepcount+=1
               if upgradeselected:
                   upgradeselected = False
                   if tsupgrade!="Ricochet" or (wave-1)>=20:
                    if (credits-1)>=0 and upgrades[tsupgrade]<upmaxes[counter]:
                            if tsupgrade == "Ricochet":
                                trueUpgrades["Piercing Bullet"] = 0
                                trueUpgrades["Bullet Speed"] = upgrades["Bullet Speed"]
                                trueUpgrades["Bullet Size"] = 0
                            if tsupgrade=="Piercing Bullet" or tsupgrade=="Bullet Speed":
                                trueUpgrades["Ricochet"] = 0
                            upgrades[tsupgrade]+=1
                            trueUpgrades[tsupgrade] +=1
                            credits-=1
                    else:
                        if (trueUpgrades[tsupgrade]+1)>upgrades[tsupgrade]:
                            trueUpgrades[tsupgrade] = 0
                            if tsupgrade == "Bullet Speed":
                                trueUpgrades["Ricochet"] = 0
                        else:
                            if tsupgrade=="Ricochet":
                                trueUpgrades["Piercing Bullet"] = 0
                                trueUpgrades["Bullet Speed"] = upgrades["Bullet Speed"]
                                trueUpgrades["Bullet Size"] = 0
                            if tsupgrade=="Piercing Bullet" or tsupgrade=="Bullet Size":
                                trueUpgrades["Ricochet"] = 0
                            trueUpgrades[tsupgrade]+=1
               if maxout:
                   maxout = False
                   trueUpgrades[tsupgrade] = upgrades[tsupgrade]
               if tsupgrade=="Ricochet":
                   if label_rect.collidepoint(mouse_x,mouse_y) and (wave-1)<20:
                        displayMessage("Unavailable until wave 20", [right_center, 500], (50, 50, 50), size=15, center=True)

               counter+=1
           if changebackground.collidepoint(mouse_x,mouse_y) and (not(cubechange) and not(changeback)):
              displayMessage("Change background colour", [right_center, 450], (50, 50, 50), size=15, center=True)
           if changecube.collidepoint(mouse_x,mouse_y) and (not(cubechange) and not(changeback)):
              displayMessage("Change player colour", [right_center, 450], (50, 50, 50), size=15, center=True)
           for event in events:
                if event.type==pygame.MOUSEBUTTONDOWN:
                    if changebackground.collidepoint(mouse_x,mouse_y):
                        choosecolour = True
                        changeback = True
                        letsprint = ""
                    if changecube.collidepoint(mouse_x,mouse_y):
                        choosecolour = True
                        cubechange = True
                        letsprint = ""
           if choosecolour:
                    letsprint = ""
                    displayMessage("Type 3 RGB values (000-255 each)", [right_center, 400], (50, 50, 50), size=12, center=True)
                    displayMessage("9 digits total, e.g. 255128064", [right_center, 418], (50, 50, 50), size=12, center=True)
                    displayMessage("Press Enter to confirm, empty Enter cancels", [right_center, 436], (50, 50, 50), size=12, center=True)
                    for printing in range(len(circleinput)):
                        if printing==0:
                            letsprint+="("
                        elif printing%3==0:
                            letsprint+=","
                        if printing==8:
                            letsprint+=str(circleinput[printing])
                            letsprint+=")"
                        else:
                            letsprint+=str(circleinput[printing])
                    if cubechange:
                        displayMessage("Player colour " + letsprint, [right_center, 470], (50, 50, 50), size=15, center=True)
                    else:
                        displayMessage("Background colour " + letsprint, [right_center, 470], (50, 50, 50), size=15, center=True)
                    letsprint = ""
                    for event in events:
                        if event.type==pygame.KEYDOWN:
                            if event.key == pygame.K_0:
                                circleinput.append("0")
                            elif event.key == pygame.K_1:
                                circleinput.append("1")
                            elif event.key == pygame.K_2:
                                circleinput.append("2")
                            elif event.key == pygame.K_3:
                                circleinput.append("3")
                            elif event.key == pygame.K_4:
                                circleinput.append("4")
                            elif event.key == pygame.K_5:
                                    circleinput.append("5")
                            elif event.key == pygame.K_6:
                                    circleinput.append("6")
                            elif event.key == pygame.K_7:
                                    circleinput.append("7")
                            elif event.key == pygame.K_8:
                                    circleinput.append("8")
                            elif event.key == pygame.K_9:
                                    circleinput.append("9")
                            elif event.key==pygame.K_RETURN:
                                    if len(circleinput)==9 or len(circleinput)==0:
                                        enterpressed=True
                            elif event.key ==pygame.K_BACKSPACE:
                                if len(circleinput)!=0:
                                    circleinput.pop()
                            if len(circleinput)%3==0:
                                checksize = ""
                                for checknum in range(len(circleinput)):
                                    checksize+=str(circleinput[checknum])
                                    if (checknum+1)%3==0:
                                        if int(checksize)>255:
                                            for x in range(3):
                                                circleinput.pop()
                                        checksize = ""
                            if len(circleinput)>9:
                                circleinput.pop()

                    if enterpressed:
                        if len(circleinput)==9:
                            newkull = [0,0,0]
                            kullcount = 0
                            singlenum = ""
                            for xc in range(9):
                                singlenum+=circleinput[xc]
                                if (xc+1)%3==0:
                                    newkull[kullcount] = int(singlenum)
                                    kullcount+=1
                                    singlenum = ""
                            yourcolour = tuple(newkull)
                            if changeback and yourcolour!=cubecolour and yourcolour!=(255,0,0):
                                background = yourcolour
                            if cubechange and yourcolour!=background:
                                cubecolour = yourcolour
                        enterpressed=False
                        choosecolour=False
                        changeback = False
                        cubechange = False
                        circleinput=[]
                        letsprint=""
               


    clock.tick(30) #How many frames happen per second i.e. how often the code above is run per second   
    pygame.display.update() #Updates the screen
pygame.quit()