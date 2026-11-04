"""逆轉金幣 桌面對戰（pygame 2D 俯視）

規則：官方取扱説明書 Ver.1.1.2 エキスパートルール（デッキ 1～3 枚・OX 合計 ≤ 15,000，メタ幣以 M 值計）
擊球：選硬幣 → 確定 → 方向 → 力量條 → 精準度條

執行：python -m pip install pygame-ce   然後   python reverse_coin.py
"""
import math
import os
import random
import sys

import pygame
from pygame import Vector2

from coin_data import BUDGET, BY_ID, COINS, PRESETS

# ---------------------------------------------------------------- 常數
SW, SH = 1280, 820
# 官方「バリ場」A3（BANDAI 公式無料配布）：297 × 420 mm；金幣直徑 43 mm
MM = 1.65                               # 1 mm = 1.65 px
FIELD_W_MM, FIELD_H_MM, COIN_MM = 297, 420, 43
FIELD = pygame.Rect(0, 0, round(FIELD_W_MM * MM), round(FIELD_H_MM * MM))
FIELD.center = (420, 418)
PANEL_X = 830
R = round(COIN_MM * MM / 2)             # 金幣半徑（px）
# 官方圖紙上的開場圓圈位置（以場地寬高比例表示）：上方 ORDER（白）、下方 XTREME（黑），約相距 6 枚金幣
START_X = (0.1816, 0.4983, 0.8150)
START_Y = {"top": 0.1240, "bottom": 0.8725}
# 撞球檯式邊框：碰到邊框時，垂直於邊框的速度 ≥ OUT_SPEED 才會飛出場外，否則回彈
RAIL = 16                               # 邊框厚度（px）
OUT_SPEED = 450.0                       # 飛出邊框的門檻速度（px/s），一定要大於翻轉門檻 UNLOCK_SPEED
RAIL_REST = 0.7                         # 邊框回彈係數
# 規則：True＝官方說明書 Ver.1.1.2（預設）；False＝isn_ver.1 自訂（攻擊方翻色不淘汰、隊友出界放回）
OFFICIAL_RULES = True
DUEL_TIME = 2.4                         # 每張 OX 對決畫面顯示秒數
FLIP_CHANCE = 0.5                       # 彈起翻轉後落地換成對方顏色的機率（正反各 1/2）
FRICTION = 650.0                        # 滑行減速 px/s²
COIN_REST = 0.95                        # 金幣互撞回彈係數（撞球約 0.93～0.98）
# 旋轉（撞球式）：單位 rad/s，金幣當均勻圓盤（轉動慣量 I = ½ m R²）
SPIN_STEP = 8.75                        # 出手旋轉每段角速度（左右各 3 段）
SPIN_DECEL = 12.0                       # 桌面摩擦讓旋轉減速（rad/s²）
COIN_MU = 0.25                          # 金幣互撞接觸摩擦：傳遞旋轉、把對手帶偏（齒輪效果）
RAIL_MU = 0.25                          # 邊框摩擦：帶旋轉撞牆改變反彈角度（塞球）
CURL_K = 0.0495                         # 旋轉中滑行的側向弧線（冰壺效果）
ACC_SPIN = 6.0                          # 精準度沒按準時額外帶出的旋轉
SPIN_ON = True                          # 旋轉物理開關（開場畫面可切換）
WATERMARK = "測試版推廣版本 請勿銷售利用｜遊戲版權歸 BANDAI 萬代所有"
PULL_MAX = 200.0                        # 後拉發射：拉 200 px（約 12 cm）＝ 100% 力量（上限）
PULL_MIN = 0.04                         # 拉不到 4% 視為取消
TURN_TIME = 18.0                        # 每回合出手限時（秒），超過＝放棄這回合
MATCH_TIME = 480.0                      # 全場 8 分鐘：時間到比開場隊伍 M 值合計，少的一方獲勝
SPIN_PERF = 0.2                         # 每加 1 段旋轉，PERFECT 區縮小 20%（3 段剩 40%）
VMIN, VMAX = 160.0, 1260.0           # 力量上限＋20%（原 1050）              # 力量 0%～100% 的初速
SPOT_HALF = math.radians(32)            # リバースポット半角（開關側與對側各一）
UNLOCK_SPEED = 280.0                    # 翻轉力道：リバースポット受到的撞擊速度 ≥ 此值才會彈起（金幣互撞、撞邊框皆同）
ACC_MAX_ERR = math.radians(70)          # 精準度條最邊緣：以發射方向為基準左右各偏 70°
ACC_CURVE = 400.0                       # 精準度偏差造成的側向弧線加速度
MISS_MIN = 5 / 70                       # 沒按進 PERFECT 區至少偏 5°
AIM_COL, TGT_COL, CUT_COL = (24, 224, 255), (255, 138, 0), (125, 255, 58)   # 輔助線：青／橘／綠
PERFECT = 0.07
SPIN_COL = (255, 79, 216)               # 旋轉指示（洋紅）


def spin_label(l):
    return "無" if l == 0 else (f"右旋 {l}" if l > 0 else f"左旋 {-l}")


COL = dict(
    bg=(22, 20, 31), panel=(34, 31, 46), panel2=(45, 41, 64), line=(70, 64, 94),
    text=(244, 242, 234), dim=(160, 155, 180), yel=(232, 255, 42), purple=(139, 92, 246),
    field=(38, 48, 58), green=(74, 222, 128), red=(248, 113, 113), amber=(250, 204, 21),
    white=(236, 234, 226), black=(22, 22, 22),
)
RAR_COL = {"RR": (192, 192, 210), "BKR": (234, 179, 8), "BBR": (217, 119, 6), "BR": (139, 92, 246),
           "R": (59, 130, 246), "C": (107, 114, 128)}
CAMP_ZH = {"O": "秩序（白）", "X": "極限（黑）"}

# ---------------------------------------------------------------- 字型
_FONTS = {}
FONT_NAMES = ["microsoftjhenghei", "microsoftjhengheiui", "notosanscjktc", "notosanscjkhk", "notosanscjk",
              "notosanstc", "pingfangtc", "pingfang", "heititc", "microsoftyahei", "simhei",
              "arialunicodems", "notosanscjksc"]


def font(size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        f = None
        for n in FONT_NAMES:
            p = pygame.font.match_font(n, bold=bold)
            if p:
                f = pygame.font.Font(p, size)
                break
        if f is None:
            f = pygame.font.Font(None, size)
        _FONTS[key] = f
    return _FONTS[key]


def text(surf, s, pos, size=18, color=COL["text"], anchor="topleft", bold=False):
    img = font(size, bold).render(str(s), True, color)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


# ---------------------------------------------------------------- 音效
SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
SOUND_EXTS = (".wav", ".ogg", ".mp3")


class Sfx:
    """sounds 資料夾裡的檔案：coin_hit（金幣互撞）、rail_hit（撞邊框）、flip（翻面）、bgm（背景音樂）。
    副檔名 .wav／.ogg／.mp3 都可以，換掉同名檔案就能換音效；檔案不見就自動靜音。"""
    NAMES = ("coin_hit", "rail_hit", "flip")

    def __init__(self):
        self.ok, self.on, self.music_on, self.snd, self.last, self.bgm = False, True, True, {}, {}, None
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            self.ok = True
        except Exception as e:                      # 沒有音效裝置也能玩
            print("音效停用：", e)
            return
        for n in self.NAMES:
            f = self.find(n)
            if f:
                try:
                    self.snd[n] = pygame.mixer.Sound(f)
                except Exception as e:
                    print("音效載入失敗：", f, e)
        self.bgm = self.find("bgm")

    @staticmethod
    def find(name):
        for ext in SOUND_EXTS:
            f = os.path.join(SOUND_DIR, name + ext)
            if os.path.exists(f):
                return f
        return None

    def play(self, name, vol=1.0):
        if not (self.ok and self.on) or name not in self.snd:
            return
        now = pygame.time.get_ticks()
        if now - self.last.get(name, -999) < 45:   # 同一種聲音太密就略過
            return
        self.last[name] = now
        ch = pygame.mixer.find_channel(True)
        if ch:
            ch.set_volume(max(0.08, min(1.0, vol)) * VOLUME["sfx"])
            ch.play(self.snd[name])

    def start_bgm(self):
        if not (self.ok and self.bgm) or pygame.mixer.music.get_busy():
            return
        try:
            pygame.mixer.music.load(self.bgm)
            pygame.mixer.music.set_volume(VOLUME["bgm"] if self.music_on else 0)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print("BGM 載入失敗：", e)

    def toggle(self):                       # 音效（碰撞、撞框、翻面）
        self.on = not self.on

    def toggle_music(self):                 # 背景音樂
        self.music_on = not self.music_on
        if self.ok:
            pygame.mixer.music.set_volume(VOLUME["bgm"] if self.music_on else 0)


VOLUME = {"sfx": 0.9, "bgm": 0.35}            # 音量（0～1）


_ARC = {}


def arc_value(surf, center, value, camp):
    """攻擊力沿金幣外圍下緣弧線排列（不擋金幣圖案）：白方白字藍框、黑方黑字黃框。"""
    key = (str(value), camp)
    if key not in _ARC:
        f = font(17, True)
        fill, stroke = ((255, 255, 255), (31, 79, 209)) if camp == "O" else ((21, 19, 28), (228, 255, 58))
        size = 2 * (R + 30)
        out = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        rb = R + 19
        chars = list(str(value))
        ws = [f.size(ch)[0] + 1 for ch in chars]
        rmid = rb - 7
        th = math.pi / 2 + sum(ws) / rmid / 2
        for ch, w in zip(chars, ws):
            a = th - w / rmid / 2
            th -= w / rmid
            g = pygame.Surface((w + 8, 26), pygame.SRCALPHA)
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    if dx * dx + dy * dy <= 5 and (dx or dy):
                        g.blit(f.render(ch, True, stroke), (4 + dx, 2 + dy))
            g.blit(f.render(ch, True, fill), (4, 2))
            r = pygame.transform.rotate(g, -(math.degrees(a) - 90))
            out.blit(r, r.get_rect(center=(c + math.cos(a) * (rb - 9), c + math.sin(a) * (rb - 9))))
        _ARC[key] = out
    img = _ARC[key]
    surf.blit(img, img.get_rect(center=(center[0], center[1])))


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def char_color(jp):
    h = sum(ord(c) * (i + 7) for i, c in enumerate(jp)) % 360
    c = pygame.Color(0)
    c.hsva = (h, 55, 85, 100)
    return c


# ---------------------------------------------------------------- 金幣圖片
# coins/<id>-o.png（白面）、coins/<id>-x.png（黑面）；圖中金幣直徑 SPRITE_COIN_D px、置中、開關朝右
SPRITE_COIN_D = 100
COIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coins")
_SPRITES = {}


def sprite(cid, face):
    key = (cid, face)
    if key not in _SPRITES:
        path = os.path.join(COIN_DIR, f"{cid}-{face}.png")
        try:
            _SPRITES[key] = pygame.image.load(path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            _SPRITES[key] = None
            zp = COIN_DIR + ".zip"                           # 沒有 coins 資料夾時改讀 coins.zip
            if os.path.exists(zp):
                try:
                    import io, zipfile
                    with zipfile.ZipFile(zp) as z:
                        data = z.read(f"{cid}-{face}.png")
                    _SPRITES[key] = pygame.image.load(io.BytesIO(data), f"{cid}-{face}.png").convert_alpha()
                except (KeyError, pygame.error, zipfile.BadZipFile):
                    pass
    return _SPRITES[key]


_FIELD_ART = []


def field_art():
    if not _FIELD_ART:
        try:
            img = pygame.image.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "field.jpg")).convert()
            _FIELD_ART.append(pygame.transform.smoothscale(img, FIELD.size))
        except (FileNotFoundError, pygame.error):
            _FIELD_ART.append(None)
    return _FIELD_ART[0]


# ---------------------------------------------------------------- 物件
class Player:
    def __init__(self, name, cpu=False):
        self.name, self.cpu = name, cpu
        self.camp = None
        self.side = "bottom"
        self.team_ids = []


class Piece:
    def __init__(self, coin, team, camp, pos, angle):
        self.coin, self.team, self.camp = coin, team, camp
        self.home_angle = angle
        self.pos, self.vel = Vector2(pos), Vector2()
        self.angle, self.spin = angle, 0.0
        self.alive, self.out = True, False
        self.reset_turn()

    def reset_turn(self):
        self.spot_speed = 0.0
        self.return_home = False
        self.spot_src = ""
        self.rail_hits = 0
        self.touched = False
        self.unlocked = False
        self.flipped = False

    @property
    def value(self):
        return self.coin.value(self.camp)

    @property
    def ox_after_pop(self):
        """彈起但外圈沒變色時，中央核心已翻面 → OX 看翻面後那一面（官方 p.7）。"""
        return self.coin.value("X" if self.camp == "O" else "O")


class Button:
    def __init__(self, rect, label, cb, enabled=None, size=22, color=None):
        self.rect, self.label, self.cb = pygame.Rect(rect), label, cb
        self.enabled = enabled or (lambda: True)
        self.size, self.color = size, color

    def draw(self, surf, mouse):
        on = self.enabled()
        hov = on and self.rect.collidepoint(mouse)
        base = self.color or COL["panel2"]
        c = tuple(min(255, v + 25) for v in base) if hov else base
        if not on:
            c = (40, 38, 50)
        if getattr(self, "alpha", None):                # 半透明底色（主選單疊在底圖上）
            tmp = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(tmp, (*c, self.alpha), tmp.get_rect(), border_radius=10)
            surf.blit(tmp, self.rect.topleft)
        else:
            pygame.draw.rect(surf, c, self.rect, border_radius=10)
        pygame.draw.rect(surf, COL["yel"] if hov else COL["line"], self.rect, 2, border_radius=10)
        text(surf, self.label, self.rect.center, self.size, COL["text"] if on else (90, 86, 104), "center", True)

    def click(self, pos):
        if self.enabled() and self.rect.collidepoint(pos):
            self.cb()
            return True
        return False


# ---------------------------------------------------------------- 遊戲
class Game:
    def __init__(self, headless=False):
        pygame.init()
        self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("逆轉金幣 Reverse Coin Battle（測試版推廣版本 請勿銷售利用）")
        self.clock = pygame.time.Clock()
        self.mouse = (0, 0)
        self.sfx = Sfx()
        self.sfx.start_bgm()
        self.players = [Player("玩家 1"), Player("玩家 2")]
        self.goto_title()

    # ============================================================ 場景切換
    def goto_title(self):
        self.scene = "title"
        cx = SW // 2
        self.buttons = [
            Button((cx - 160, 360, 320, 60), "雙人對戰（同一台電腦）", lambda: self.start_match(False), size=24),
            Button((cx - 160, 432, 320, 60), "對戰電腦", lambda: self.start_match(True), size=24),
            Button((cx - 160, 504, 320, 60), "旋轉物理：開（撞球式）" if SPIN_ON else "旋轉物理：關（經典）", self.toggle_spin,
                   size=22, color=(75, 40, 95) if SPIN_ON else None),
            Button((cx - 160, 576, 320, 60), "規則說明", self.goto_rules, size=24),
            Button((cx - 160, 648, 320, 60), "離開", self.quit, size=24),
        ]
        for b in self.buttons:                       # 主選單按鈕半透明
            b.alpha = 215

    def title_bg(self):
        """主選單底圖：官方バリ場（裁成畫面大小）＋深色漸層。"""
        if getattr(self, "_title_bg", None) is None:
            bg = pygame.Surface((SW, SH))
            bg.fill(COL["bg"])
            try:
                img = pygame.image.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "field.jpg")).convert()
                sc = max(SW / img.get_width(), SH / img.get_height())
                img = pygame.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
                bg.blit(img, ((SW - img.get_width()) // 2, (SH - img.get_height()) // 2))
            except Exception:
                pass
            shade = pygame.Surface((SW, SH), pygame.SRCALPHA)
            for y in range(SH):
                shade.fill((10, 8, 16, int(120 + 80 * y / SH)), (0, y, SW, 1))
            bg.blit(shade, (0, 0))
            self._title_bg = bg
        return self._title_bg

    def toggle_spin(self):
        global SPIN_ON
        SPIN_ON = not SPIN_ON
        self.goto_title()

    def goto_rules(self, page=0):
        self.scene = "rules"
        if not hasattr(self, "rule_imgs"):
            d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules_img")
            self.rule_imgs = []
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if f.endswith(".png"):
                    try:
                        self.rule_imgs.append(pygame.image.load(os.path.join(d, f)).convert_alpha())
                    except Exception:
                        pass
        n = max(1, math.ceil(len(self.rule_imgs) / 8))
        self.rule_page = max(0, min(n - 1, page))
        self.buttons = [Button((SW // 2 - 120, SH - 84, 240, 50), "返回", self.goto_title)]
        if n > 1:
            self.buttons += [Button((SW // 2 - 300, SH - 84, 160, 50), "◀ 上一頁", lambda: self.goto_rules(self.rule_page - 1),
                                    lambda: self.rule_page > 0),
                             Button((SW // 2 + 140, SH - 84, 160, 50), "下一頁 ▶", lambda: self.goto_rules(self.rule_page + 1),
                                    lambda: self.rule_page < n - 1)]

    def start_match(self, vs_cpu):
        self.players = [Player("玩家 1"), Player("電腦" if vs_cpu else "玩家 2", cpu=vs_cpu)]
        self.goto_build(0)                      # 官方：先決定デッキ，再決定サイドと先攻後攻

    def goto_rps(self):
        self.scene = "rps"
        hands = ["石頭", "剪刀", "布"]
        while True:
            a, b = random.randrange(3), random.randrange(3)
            if a != b:
                break
        self.rps_hands = (hands[a], hands[b])
        self.rps_winner = 0 if (a - b) % 3 == 2 else 1
        self.rps_stage = "pick"         # pick → toss
        self.cpu_timer = 1.2
        w = self.players[self.rps_winner]
        self.buttons = [] if w.cpu else [
            Button((SW // 2 - 330, 470, 300, 80), "選 秩序（白）", lambda: self.pick_camp("O"), size=26,
                   color=(120, 118, 110)),
            Button((SW // 2 + 30, 470, 300, 80), "選 極限（黑）", lambda: self.pick_camp("X"), size=26,
                   color=(10, 10, 10)),
        ]

    def pick_camp(self, camp):
        w = self.rps_winner
        self.players[w].camp = camp
        self.players[1 - w].camp = "X" if camp == "O" else "O"
        self.first_camp = random.choice("OX")
        self.rps_stage = "toss"
        self.buttons = [Button((SW // 2 - 140, 640, 280, 64), "開始對戰", self.goto_battle, size=24)]

    def goto_build(self, idx):
        p = self.players[idx]
        if p.cpu:
            p.team_ids = list(PRESETS[0][1])    # 電腦還不知道陣營 → 帶非メタ的平衡隊
            if idx == 0:
                return self.goto_build(1)
            return self.goto_rps()
        self.scene = "build"
        self.build_idx = idx
        self.sel = list(p.team_ids)
        self.flt_side, self.flt_rar, self.sort_mode, self.scroll = "全部", "全部", "戰力", 0
        self.q, self.q_active, self.min_s, self.max_s, self.fit_only = "", False, 0, 0, False   # 搜尋／分數過濾（0＝不限）
        self.row_rects, self.slot_rects = [], []
        self.make_build_buttons()

    def make_build_buttons(self):
        b = []
        x = 40
        for s in ["全部", "白主", "黑主"]:
            b.append(Button((x, 80, 64, 34), s, lambda s=s: self.set_flt("side", s), size=16))
            x += 68
        x += 12
        for r in ["全部", "RR", "BKR", "BBR", "BR", "R", "C"]:
            b.append(Button((x, 80, 52, 34), r, lambda r=r: self.set_flt("rar", r), size=15))
            x += 56
        x += 12
        for s in ["戰力", "預算"]:
            b.append(Button((x, 80, 60, 34), "依" + s, lambda s=s: self.set_flt("sort", s), size=15))
            x += 64
        # 第二列：搜尋框（畫在 draw_build）＋分數範圍＋預算內
        sx = 40 + 300 + 10
        self.min_btn = Button((sx, 122, 118, 34), "", lambda: self.cycle_score("min", 1), size=15)
        self.max_btn = Button((sx + 124, 122, 118, 34), "", lambda: self.cycle_score("max", 1), size=15)
        self.fit_btn = Button((sx + 248, 122, 108, 34), "只看預算內", self.toggle_fit, size=15)
        clr = Button((sx + 362, 122, 88, 34), "清除過濾", self.clear_search, size=15)
        b += [self.min_btn, self.max_btn, self.fit_btn, clr]
        self.update_score_labels()
        px = PANEL_X + 10
        y = 380
        for name, ids in PRESETS:
            b.append(Button((px, y, 410, 38), "套用：" + name, lambda ids=ids: self.apply_preset(ids), size=17))
            y += 44
        b.append(Button((px, 630, 196, 50), "清除", lambda: self.sel.clear(), size=20))
        b.append(Button((px + 214, 630, 196, 50), "確定デッキ", self.confirm_build, self.build_ok, size=20,
                        color=(80, 60, 160)))
        b.append(Button((px, 700, 410, 44), "返回標題", self.goto_title, size=18))
        self.buttons = b

    SCORES = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]

    def cycle_score(self, which, d):
        k = "min_s" if which == "min" else "max_s"
        i = (self.SCORES.index(getattr(self, k)) + d) % len(self.SCORES)
        setattr(self, k, self.SCORES[i])
        if self.max_s and self.min_s > self.max_s:
            if which == "min":
                self.max_s = 0                       # 最低超過最高 → 最高改成不限
            else:
                self.max_s = self.min_s              # 最高不能低於最低
        self.scroll = 0
        self.update_score_labels()

    def update_score_labels(self):
        self.min_btn.label = f"最低 {self.min_s if self.min_s else '不限'}"
        self.max_btn.label = f"最高 {self.max_s if self.max_s else '不限'}"
        self.fit_btn.color = (80, 60, 160) if self.fit_only else None

    def toggle_fit(self):
        self.fit_only = not self.fit_only
        self.scroll = 0
        self.update_score_labels()

    def clear_search(self):
        self.q, self.min_s, self.max_s, self.fit_only, self.scroll = "", 0, 0, False, 0
        self.update_score_labels()

    def set_flt(self, k, v):
        if k == "side":
            self.flt_side = v
        elif k == "rar":
            self.flt_rar = v
        else:
            self.sort_mode = v
        self.scroll = 0

    def apply_preset(self, ids):
        self.sel = list(ids)

    def build_cost(self):
        return sum(BY_ID[i].cost for i in self.sel)

    def build_ok(self):
        return 1 <= len(self.sel) <= 3 and len(set(self.sel)) == len(self.sel) and self.build_cost() <= BUDGET

    def confirm_build(self):
        self.players[self.build_idx].team_ids = list(self.sel)
        if self.build_idx == 0:
            self.goto_build(1)
        else:
            self.goto_rps()

    def filtered(self):
        q = getattr(self, "q", "").strip().lower()
        lo, hi = getattr(self, "min_s", 0), getattr(self, "max_s", 0) or 99999
        left = BUDGET - self.build_cost()
        lst = [c for c in COINS
               if (self.flt_side == "全部" or c.main == {"白主": "O", "黑主": "X"}[self.flt_side])
               and (self.flt_rar == "全部" or c.rarity == self.flt_rar)
               and lo <= c.cost <= hi                                   # 分數＝組隊計分（メタ幣為 M 值）
               and (not getattr(self, "fit_only", False) or c.id in self.sel or c.cost <= left)
               and (not q or any(q in str(t).lower() for t in (c.jp, c.zh, c.set, c.rarity, c.id, c.o, c.x)))]
        top = lambda c: max(c.o, c.x)
        if self.sort_mode == "戰力":
            lst.sort(key=lambda c: (-top(c), c.cost))
        else:
            lst.sort(key=lambda c: (c.cost, -top(c)))
        return lst

    # ============================================================ 對戰
    def toggle_sound(self):
        self.sfx.toggle()
        if hasattr(self, "sound_btn"):
            self.sound_btn.label = "音效：開" if self.sfx.on else "音效：關"

    def toggle_music(self):
        self.sfx.toggle_music()
        if hasattr(self, "music_btn"):
            self.music_btn.label = "音樂：開" if self.sfx.music_on else "音樂：關"

    def add_spin(self, d):
        if SPIN_ON:
            self.spin_lvl = max(-3, min(3, getattr(self, "spin_lvl", 0) + d))

    def toggle_guide(self):
        self.guide = not self.guide
        self.guide_btn.label = "輔助線：開" if self.guide else "輔助線：關"

    def goto_battle(self):
        self.scene = "battle"
        if not hasattr(self, "guide"):
            self.guide = True
        self.guide_btn = Button((FIELD.right - 132, 14, 132, 34), "輔助線：開" if self.guide else "輔助線：關",
                                self.toggle_guide, size=16)
        self.sound_btn = Button((PANEL_X + 290, 22, 132, 34), "音效：開" if self.sfx.on else "音效：關",
                                self.toggle_sound, size=16)
        self.music_btn = Button((PANEL_X + 150, 22, 132, 34), "音樂：開" if self.sfx.music_on else "音樂：關",
                                self.toggle_music, size=16)
        self.buttons = [self.guide_btn, self.sound_btn, self.music_btn]
        if SPIN_ON:
            ok = lambda: self.cur() and not self.cur().cpu and self.phase in ("select", "aim", "power")
            self.spin_btns = [Button((0, -100, 96, 30), "◀ 左旋", lambda: self.add_spin(-1), ok, size=15),
                              Button((0, -100, 96, 30), "右旋 ▶", lambda: self.add_spin(1), ok, size=15)]
            self.buttons += self.spin_btns
        else:
            self.spin_btns = []
        self.pieces = []
        for t, p in enumerate(self.players):
            p.side = "top" if p.camp == "O" else "bottom"      # 官方圖紙：上 ORDER、下 XTREME
            y = FIELD.y + START_Y[p.side] * FIELD.h
            ang = 0.0 if p.side == "bottom" else math.pi      # 開關朝自己的右手邊
            slots = {1: [1], 2: [0, 2]}.get(len(p.team_ids), [0, 1, 2])
            for k, cid in enumerate(p.team_ids):
                x = FIELD.x + START_X[slots[k]] * FIELD.w
                self.pieces.append(Piece(BY_ID[cid], t, p.camp, (x, y), ang))
        self.turn = 0 if self.players[0].camp == self.first_camp else 1
        self.log = [f"擲金幣：{CAMP_ZH[self.first_camp]} 先攻"]
        self.match_t, self.time_result = MATCH_TIME, None
        self.winner = None
        self.begin_turn()

    def begin_turn(self):
        for p in self.pieces:
            p.reset_turn()
        self.phase = "select"
        own = self.own_alive()
        self.selected = own[0] if own else None
        self.aim = -math.pi / 2 if self.cur().side == "bottom" else math.pi / 2
        self.power, self.pdir = 0.0, 1
        self.acc, self.adir = -1.0, 1
        self.spin_lvl = 0
        self.shooter = None
        self.place_queue = []
        self.place_rot = 0.0
        self.cpu_timer = 0.7
        self.cpu_plan = None
        self.result_lines = []
        self.turn_t, self.pull = TURN_TIME, None

    def cur(self):
        return self.players[self.turn]

    def own_alive(self, team=None):
        t = self.turn if team is None else team
        return [p for p in self.pieces if p.alive and p.team == t]

    def field_pieces(self):
        return [p for p in self.pieces if p.alive and not p.out]

    # ------------------------------------------------------------ 擊球流程
    def confirm_select(self):
        if self.selected:
            self.phase, self.power = "aim", 0.0

    def confirm_aim(self):
        self.phase = "power"
        self.power, self.pdir = 0.0, 1

    def lock_power(self):
        self.phase = "accuracy"
        self.acc, self.adir = -1.0, 1

    @staticmethod
    def perf_zone(lvl=0):
        """旋轉越強，PERFECT 區越窄。"""
        return PERFECT * max(0.1, 1 - SPIN_PERF * abs(lvl))

    @staticmethod
    def acc_err(a, zone=PERFECT):
        """PERFECT 區內 0；一離開就至少偏 MISS_MIN，越靠邊越大（最多 ACC_MAX_ERR）。"""
        m = abs(a)
        if m <= zone:
            return 0.0
        t = (m - zone) / (1 - zone)
        return math.copysign(MISS_MIN + (1 - MISS_MIN) * t, a)

    def lock_acc(self):
        s = self.selected
        lvl = getattr(self, "spin_lvl", 0) if SPIN_ON else 0
        err = self.acc_err(self.acc, self.perf_zone(lvl))
        if err == 0:
            self.add_log("精準度 PERFECT！")
        ang = self.aim + err * ACC_MAX_ERR
        speed = VMIN + self.power * (VMAX - VMIN)
        s.vel = Vector2(math.cos(ang), math.sin(ang)) * speed
        self.curve = err * ACC_CURVE
        s.spin = (lvl * SPIN_STEP + err * ACC_SPIN) if SPIN_ON else 0.0            # 出手旋轉（塞球）＋沒按準的額外旋轉
        self.shooter = s
        self.shooter_hit = False
        for p in self.pieces:
            p.prev_pos = Vector2(p.pos)
        self.phase = "moving"
        self.add_log(f"{s.coin.jp} 出手：力量 {int(self.power * 100)}%｜旋轉 {spin_label(lvl)}｜偏角 {math.degrees(err * ACC_MAX_ERR):+.1f}°")

    # ------------------------------------------------------------ 物理
    def physics(self, dt):
        live = [p for p in self.pieces if p.alive]
        for p in live:
            sp = p.vel.length()
            if sp > 0:
                if p is self.shooter and not self.shooter_hit and self.curve:
                    perp = Vector2(-p.vel.y, p.vel.x) / sp
                    p.vel += perp * self.curve * dt
                    sp = p.vel.length()
                dec = FRICTION * dt
                p.vel = Vector2() if sp <= dec else p.vel * ((sp - dec) / sp)
            if p.spin and sp > 0:                 # 旋轉中滑行 → 側向弧線（冰壺效果）
                k = CURL_K * p.spin * dt
                p.vel = Vector2(p.vel.x - p.vel.y * k, p.vel.y + p.vel.x * k)
            if p.spin:
                d = SPIN_DECEL * dt
                p.spin = 0.0 if abs(p.spin) <= d else p.spin - math.copysign(d, p.spin)
            p.pos += p.vel * dt
            p.angle += p.spin * dt
            if not p.out:
                self.rail_bounce(p)
            if p.out:
                p.pos.x = max(14, min(PANEL_X - R + 2, p.pos.x))
                p.pos.y = max(52, min(SH - 14, p.pos.y))
        inside = [p for p in live if not p.out]
        for _ in range(2):                      # 多次迭代：處理三顆以上擠在一起的連鎖碰撞
            for i in range(len(inside)):
                for j in range(i + 1, len(inside)):
                    self.collide(inside[i], inside[j])

    def collide(self, a, b):
        """撞球式碰撞：等質量、沿連心線傳遞動量（正面撞擊時母球幾乎停住），
        切線方向保留（分球角度約 90°），加上少量摩擦（throw）與旋轉。"""
        d = b.pos - a.pos
        dist = d.length()
        if dist == 0 or dist >= 2 * R:
            return
        n = d / dist
        ov = 2 * R - dist
        a.pos -= n * (ov / 2)
        b.pos += n * (ov / 2)
        rel = (a.vel - b.vel).dot(n)
        if rel <= 0:
            return
        jn = rel * (1 + COIN_REST) / 2               # 法向衝量（等質量）
        self.sfx.play("coin_hit", rel / 700)
        a.vel -= n * jn
        b.vel += n * jn
        # 接觸點切向相對速度＝平移差＋兩枚旋轉（ω×R）；摩擦衝量受 COIN_MU·法向衝量限制
        t = Vector2(-n.y, n.x)
        vt = (a.vel - b.vel).dot(t) + R * (a.spin + b.spin)
        jt = max(-COIN_MU * jn, min(COIN_MU * jn, -vt / 6))   # 有效質量 1+1+2+2 = 6
        a.vel += t * jt
        b.vel -= t * jt
        a.spin += 2 * jt / R                         # 齒輪效果：兩枚往相反方向轉
        b.spin += 2 * jt / R
        if not SPIN_ON:
            a.spin = b.spin = 0.0
        self.record_hit(a, n, rel)
        self.record_hit(b, -n, rel)
        if self.shooter in (a, b):
            self.shooter_hit = True

    def spot_facing(self, p, direction):
        """direction（從金幣中心指向受力點）是否落在リバースポット（開關側或正對側）。"""
        d = abs(angle_diff(math.atan2(direction.y, direction.x), p.angle))
        return min(d, math.pi - d) <= SPOT_HALF

    def record_hit(self, p, direction, rel):
        p.touched = True
        if self.spot_facing(p, direction) and rel > p.spot_speed:
            p.spot_speed, p.spot_src = rel, "coin"

    def rail_bounce(self, p):
        """撞球檯式邊框，三種情形：
        1) 垂直撞擊速度 ≥ OUT_SPEED → 飛越邊框出界
        2) 否則依 RAIL_REST 減少動能後反彈
        3) 反彈時若是自己的リバースポット撞到邊框、且速度 ≥ UNLOCK_SPEED → 也會彈起翻轉"""
        for axis, lo, hi in ((0, FIELD.left + R, FIELD.right - R), (1, FIELD.top + R, FIELD.bottom - R)):
            pos = p.pos[axis]
            if lo <= pos <= hi:
                continue
            vn = -p.vel[axis] if pos < lo else p.vel[axis]
            if vn <= 0:
                continue
            self.sfx.play("rail_hit", vn / 500)
            if vn >= OUT_SPEED:
                p.out = True
                p.vel *= 0.55          # 飛越邊框損失速度
                return
            outward = Vector2(0, 0)
            outward[axis] = -1 if pos < lo else 1
            if vn >= UNLOCK_SPEED and self.spot_facing(p, outward) and vn > p.spot_speed:
                p.spot_speed, p.spot_src = vn, "rail"
            p.pos[axis] = lo if pos < lo else hi
            p.vel[axis] = -p.vel[axis] * RAIL_REST
            # 邊框摩擦：接觸點切向速度（含旋轉）→ 改變反彈角度與旋轉（塞球）
            t = Vector2(-outward.y, outward.x)
            jn = vn * (1 + RAIL_REST)
            vt = p.vel.dot(t) + p.spin * R
            jt = max(-RAIL_MU * jn, min(RAIL_MU * jn, -vt / 3))  # 有效質量 1 + 2 = 3
            p.vel += t * jt
            p.spin += 2 * jt / R if SPIN_ON else 0.0
            p.rail_hits += 1

    def all_stopped(self):
        return all(p.vel.length() < 3 and abs(p.spin) < 0.4 for p in self.pieces if p.alive)

    # ------------------------------------------------------------ 判定
    def start_resolve(self):
        for p in self.pieces:
            p.vel = Vector2()
            p.spin = 0
            if p.alive and p.spot_speed >= UNLOCK_SPEED:
                p.unlocked = True
                p.flipped = random.random() < FLIP_CHANCE      # 彈起後落地：正反面各 1/2
                how = "撞到邊框" if p.spot_src == "rail" else "被撞到"
                self.add_log(f"{p.coin.jp} 的リバースポット{how}（力道 {int(p.spot_speed)}）→ 彈起")
        if any(p.unlocked for p in self.pieces):
            self.phase = "jump"
            self.sfx.play("flip", 1.0)
            self.jump_t = 0.0
        else:
            self.apply_results()

    def eliminate(self, p, why):
        p.alive = False
        self.add_log(f"淘汰｜{p.coin.jp}（{p.value}）{why}")

    def apply_results(self):
        S = self.shooter
        A = S.team
        self.events = []
        if not self.shooter_hit and not S.out:
            self.add_log("沒碰到任何金幣 → 無效攻擊，原地重新鎖定")
        elif self.shooter_hit and not any(p.unlocked or p.out for p in self.pieces if p.alive):
            self.add_log("有碰撞但沒打中リバースポット → 沒有翻轉，比賽繼續")
        for p in list(self.pieces):
            if not p.alive:
                continue
            if p.team == A:
                # 攻擊方（官方 p.8～9）：自己回合自己的金幣出界＝自滅 OUT；自爆翻成對方顏色＝OUT；自爆仍是自己顏色＝セーフ放回原位
                if p is S and p.out:
                    self.eliminate(p, "攻擊方出界 → 淘汰（自滅）")
                elif p.out:
                    if OFFICIAL_RULES:
                        self.eliminate(p, "攻擊方隊友被自己撞出界 → 淘汰（自滅）")
                    else:
                        self.add_log(f"{p.coin.jp}（攻擊方隊友）被撞出界 → 不淘汰，由攻擊方安排回場")
                        self.place_queue.append(p)
                elif p.unlocked and p.flipped and OFFICIAL_RULES:
                    self.eliminate(p, "自爆翻成對方顏色 → 淘汰")
                elif p.unlocked:
                    side = "翻成對方顏色 → 不淘汰（isn_ver.1）" if p.flipped else "仍是自己顏色 → セーフ"
                    self.add_log(f"{p.coin.jp}（攻擊方）自爆{side}，原地重新鎖定")
                    p.return_home = True
            else:
                if not p.unlocked:
                    if p.out:
                        self.add_log(f"存活｜{p.coin.jp} 被擊出界、沒翻面 → 存活，由攻擊方安排回場")
                        self.place_queue.append(p)
                elif p.flipped:
                    self.eliminate(p, "翻成對方顏色 → 淘汰")
                    self.events.append(("flip", S, p, False))
                else:
                    v = p.ox_after_pop
                    meta = f"（メタ幣核心翻面：{p.value}→{v}）" if p.coin.meta else ""
                    if v >= S.value:
                        self.add_log(f"存活｜{p.coin.jp} 仍是自己顏色，OX {v} ≥ {S.value} → 存活{meta}")
                        self.events.append(("duel", S, p, True))
                        if p.out:
                            self.place_queue.append(p)
                        else:
                            p.return_home = True
                    else:
                        self.eliminate(p, f"仍是自己顏色，OX {v} < {S.value} → 淘汰{meta}")
                        self.events.append(("duel", S, p, False))
        for p in self.pieces:
            if p.alive and not p.out:
                p.angle = p.home_angle if p.unlocked else p.angle
        # 彈起但セーフ：留在停下的位置，原地重新鎖定（判定助手 D6／A4）
        for p in self.pieces:
            p.return_home = False
        self.place_queue = [p for p in self.place_queue if p.alive]
        if self.events:
            self.phase, self.duel_t = "duel", 0.0          # 先播放 OX 對決／翻面畫面
            return
        self.after_results()

    def after_results(self):
        if self.check_win():
            return
        if self.place_queue:
            self.phase = "place"
            self.cpu_timer = 0.6
            self.turn_t = TURN_TIME
        else:
            self.end_turn()

    def return_to_prev(self, p):
        target = getattr(p, "prev_pos", None)
        if target is None:
            return
        inner = FIELD.inflate(-2 * R, -2 * R)

        def free(v):
            return all(q is p or q.pos.distance_to(v) >= 2 * R + 1 for q in self.field_pieces())

        if not free(target):                       # 原位被佔用時，往外找最近的空位
            for rad in range(8, 300, 8):
                cands = [target + Vector2(math.cos(a / 16 * math.tau), math.sin(a / 16 * math.tau)) * rad
                         for a in range(16)]
                ok = [c for c in cands if inner.collidepoint(c) and free(c)]
                if ok:
                    target = ok[0]
                    break
        p.pos = Vector2(target)

    def place_valid(self, pos, piece):
        inner = FIELD.inflate(-2 * R, -2 * R)
        if not inner.collidepoint(pos):
            return False
        for q in self.field_pieces():
            if q is not piece and q.pos.distance_to(pos) < 4 * R:
                return False
        return True

    def place(self, pos):
        p = self.place_queue[0]
        if not self.place_valid(pos, p):
            return
        p.pos, p.out, p.vel, p.angle = Vector2(pos), False, Vector2(), p.home_angle + self.place_rot
        self.place_rot = 0.0
        self.place_queue.pop(0)
        if not self.place_queue:
            self.end_turn()

    def check_win(self):
        a = [len(self.own_alive(t)) for t in (0, 1)]
        if a[0] == 0 or a[1] == 0:
            self.winner = -1 if a[0] == a[1] else (0 if a[1] == 0 else 1)
            self.phase = "over"
            self.buttons = [
                Button((FIELD.centerx - 230, 470, 220, 60), "同隊再戰", self.goto_battle, size=22),
                Button((FIELD.centerx + 10, 470, 220, 60), "回標題", self.goto_title, size=22),
            ]
            return True
        return False

    def team_m(self, t):
        return sum(BY_ID[i].cost for i in self.players[t].team_ids)

    def match_time_up(self):
        """全場時間到：比開場隊伍的 M 值合計，少的一方獲勝（相同＝平手）。"""
        a, b = self.team_m(0), self.team_m(1)
        self.time_result = (a, b)
        self.add_log(f"⏱ 全場 8 分鐘時間到 → 開場 M 值合計 {self.players[0].name} {a:,}／{self.players[1].name} {b:,}")
        self.winner = -1 if a == b else (0 if a < b else 1)
        self.phase = "over"
        self.buttons = [
            Button((FIELD.centerx - 230, 500, 220, 60), "同隊再戰", self.goto_battle, size=22),
            Button((FIELD.centerx + 10, 500, 220, 60), "回標題", self.goto_title, size=22),
        ]

    def time_up(self):
        """出手限時到：放回場階段自動放置；其他階段＝放棄這回合。"""
        if self.phase == "place":
            p = self.place_queue[0]
            for _ in range(800):
                pos = Vector2(random.uniform(FIELD.left + R, FIELD.right - R), random.uniform(FIELD.top + R, FIELD.bottom - R))
                if self.place_valid(pos, p):
                    self.add_log(f"時間到 → {p.coin.jp} 自動放回場內")
                    self.place(pos)
                    return
            return
        self.add_log(f"⏱ {self.cur().name} 超過 {int(TURN_TIME)} 秒沒有出手 → 放棄這回合，換對方進攻")
        self.pull = None
        self.end_turn()

    def end_turn(self):
        for p in self.pieces:
            if p.out and p.alive:
                p.alive = False
        if getattr(self, "match_t", 1) <= 0:          # 全場時間到：在回合交換時結束
            self.match_time_up()
            return
        self.turn = 1 - self.turn
        self.begin_turn()

    def add_log(self, s):
        self.log.append(s)
        self.log = self.log[-60:]

    # ------------------------------------------------------------ 電腦
    def cpu_plan_shot(self):
        own, enemy = self.own_alive(), self.own_alive(1 - self.turn)
        best = None
        for s in own:
            for t in enemy:
                to_s = s.pos - t.pos
                cands = [t.pos + to_s.normalize() * 2 * R] if to_s.length() else []
                for base in (t.angle, t.angle + math.pi):
                    u = Vector2(math.cos(base), math.sin(base))
                    if u.dot(to_s) > 0:
                        cands.append((t.pos + u * 2 * R, True))
                for c in cands:
                    spot = False
                    if isinstance(c, tuple):
                        c, spot = c
                    dist = s.pos.distance_to(c)
                    if dist < 1:
                        continue
                    score = -dist * 0.01 + (6 if spot else 0) + (3 if s.value > t.value else 0)
                    if best is None or score > best[0]:
                        best = (score, s, c, dist)
        if best is None:
            return
        _, s, c, dist = best
        need = math.sqrt(430 ** 2 + 2 * FRICTION * dist)
        power = max(0.05, min(1.0, (need - VMIN) / (VMAX - VMIN)))
        d = c - s.pos
        self.cpu_plan = dict(piece=s, aim=math.atan2(d.y, d.x),
                             power=max(0.0, min(1.0, power + random.gauss(0, 0.05))),
                             acc=max(-1.0, min(1.0, random.gauss(0, 0.22))))
        self.selected = s

    def cpu_update(self, dt):
        self.cpu_timer -= dt
        ph = self.phase
        if ph == "select" and self.cpu_timer <= 0:
            self.cpu_plan_shot()
            self.phase, self.cpu_timer, self.power = "aim", 0.9, 0.0
        elif ph == "aim" and self.cpu_plan:
            self.aim += angle_diff(self.cpu_plan["aim"], self.aim) * min(1, dt * 6)
            self.power += (self.cpu_plan["power"] - self.power) * min(1, dt * 4)   # 看起來像在後拉
            if self.cpu_timer <= 0:
                self.aim, self.power = self.cpu_plan["aim"], self.cpu_plan["power"]
                self.lock_power()
        elif ph == "power" and self.cpu_plan:
            self.power = self.cpu_plan["power"]
            self.lock_power()
        elif ph == "accuracy" and self.cpu_plan:
            if abs(self.acc - self.cpu_plan["acc"]) < 0.04:
                self.lock_acc()
        elif ph == "place" and self.cpu_timer <= 0:
            p = self.place_queue[0]
            for _ in range(400):
                pos = Vector2(random.uniform(FIELD.left + R, FIELD.right - R),
                              random.uniform(FIELD.top + R, FIELD.bottom - R))
                if self.place_valid(pos, p):
                    self.add_log(f"電腦把 {p.coin.jp} 放回場內")
                    self.place(pos)
                    break
            self.cpu_timer = 0.4

    # ============================================================ 迴圈
    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000, 1 / 30)
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def handle(self, e):
        if e.type == pygame.QUIT:
            self.quit()
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in list(self.buttons):
                if b.click(e.pos):
                    return
        typing = self.scene == "build" and getattr(self, "q_active", False)
        if e.type == pygame.KEYDOWN and e.key == pygame.K_m and not typing:
            self.toggle_music()
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_n and not typing:
            self.toggle_sound()
            return
        if self.scene == "build":
            self.handle_build(e)
        elif self.scene == "battle":
            self.handle_battle(e)
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.scene == "rules":
            self.goto_title()

    def handle_build(self, e):
        # 搜尋框：點一下開始輸入（支援中文／日文輸入法），Enter／Esc 結束
        box = pygame.Rect(40, 122, 300, 34)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.q_active = box.collidepoint(e.pos)
            if self.q_active:
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(box)
        if self.q_active:
            if e.type == pygame.TEXTINPUT:
                self.q += e.text
                self.scroll = 0
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.q = self.q[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_KP_ENTER):
                    self.q_active = False
                self.scroll = 0
                return
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y * 3)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for rect, c in self.row_rects:
                if rect.collidepoint(e.pos):
                    if c.id in self.sel:           # 同一隊不可重複：再點一次取消
                        self.sel.remove(c.id)
                    elif len(self.sel) < 3:
                        self.sel.append(c.id)
                    return
            for k, (rect, cid) in enumerate(self.slot_rects):
                if rect.collidepoint(e.pos) and k < len(self.sel):
                    self.sel.pop(k)
                    return

    def handle_battle(self, e):
        if self.phase == "duel":
            if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or (
                    e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN)):
                k = int(self.duel_t // DUEL_TIME) + 1
                self.duel_t = k * DUEL_TIME                 # 跳到下一張
                if k >= len(self.events):
                    self.after_results()
            return
        if self.phase == "over" or self.cur().cpu:
            return
        click = e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
        key = e.key if e.type == pygame.KEYDOWN else None
        go = click or key in (pygame.K_SPACE, pygame.K_RETURN)
        ph = self.phase
        if key in (pygame.K_z, pygame.K_x) and ph in ("select", "aim", "power") and SPIN_ON:
            self.spin_lvl = max(-3, min(3, self.spin_lvl + (-1 if key == pygame.K_z else 1)))
            return
        # 後拉發射：在選金幣／瞄準階段按住滑鼠往反方向拉，放開進入精準度
        if ph in ("select", "aim") and click and e.pos[0] < PANEL_X:
            for p in self.own_alive():
                if p.pos.distance_to(e.pos) <= R + 4 and p is not self.selected:
                    self.selected = p
            if self.selected:
                self.phase, self.power, self.pull = "aim", 0.0, Vector2(e.pos)
            return
        if ph == "aim" and self.pull is not None and e.type == pygame.MOUSEMOTION:
            d = self.pull - Vector2(e.pos)
            self.power = max(0.0, min(1.0, d.length() / PULL_MAX))
            if d.length() > 5:
                self.aim = math.atan2(d.y, d.x)
            return
        if ph == "aim" and self.pull is not None and e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.pull = None
            if self.power >= PULL_MIN:
                self.lock_power()
            else:
                self.power = 0.0
            return
        if ph == "select":
            own = self.own_alive()
            if key == pygame.K_TAB and own:
                i = own.index(self.selected) if self.selected in own else -1
                self.selected = own[(i + 1) % len(own)]
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.confirm_select()
        elif key in (pygame.K_z, pygame.K_x) and ph in ("select", "aim", "power"):
            self.spin_lvl = max(-3, min(3, self.spin_lvl + (-1 if key == pygame.K_z else 1)))
            return
        elif key == pygame.K_h and ph in ("aim", "power", "accuracy", "select"):
            self.toggle_guide()
        elif ph == "aim":                               # 鍵盤：←→ 方向、↑↓ 力量、Space 發射
            if key == pygame.K_ESCAPE:
                self.phase, self.pull, self.power = "select", None, 0.0
            elif key == pygame.K_LEFT:
                self.aim -= math.radians(1)
            elif key == pygame.K_RIGHT:
                self.aim += math.radians(1)
            elif key == pygame.K_UP:
                self.power = min(1.0, self.power + 0.05)
            elif key == pygame.K_DOWN:
                self.power = max(0.0, self.power - 0.05)
            elif key in (pygame.K_SPACE, pygame.K_RETURN) and self.power >= PULL_MIN:
                self.lock_power()
        elif ph == "power" and go:
            self.lock_power()
        elif ph == "accuracy" and go:
            self.lock_acc()
        elif ph == "place" and click:
            self.place(Vector2(e.pos))
        elif ph == "place" and key in (pygame.K_q, pygame.K_e):
            self.place_rot += (-1 if key == pygame.K_q else 1) * math.pi / 8

    def update(self, dt):
        if self.scene == "rps" and self.players[self.rps_winner].cpu and self.rps_stage == "pick":
            self.cpu_timer -= dt
            if self.cpu_timer <= 0:
                self.pick_camp(random.choice("OX"))
        if self.scene != "battle":
            return
        ph = self.phase
        if ph != "over" and hasattr(self, "match_t"):
            self.match_t = max(0.0, self.match_t - dt)
        if ph in ("select", "aim", "power", "accuracy", "place") and hasattr(self, "turn_t"):
            self.turn_t = max(0.0, self.turn_t - dt)
            if self.turn_t <= 0:
                self.time_up()
                return
        if ph == "power":
            self.power += self.pdir * dt * 0.9
            if self.power >= 1:
                self.power, self.pdir = 1.0, -1
            if self.power <= 0:
                self.power, self.pdir = 0.0, 1
        elif ph == "accuracy":
            self.acc += self.adir * dt * 1.7
            if self.acc >= 1:
                self.acc, self.adir = 1.0, -1
            if self.acc <= -1:
                self.acc, self.adir = -1.0, 1
        elif ph == "moving":
            vmax = max((p.vel.length() for p in self.pieces if p.alive), default=0)
            n = max(4, min(40, math.ceil(vmax * dt / (R * 0.25))))   # 高速時細分，避免穿透
            for _ in range(n):
                self.physics(dt / n)
            if self.all_stopped():
                self.start_resolve()
        elif ph == "jump":
            self.jump_t += dt / 0.9
            if self.jump_t >= 1:
                self.apply_results()
        elif ph == "duel":
            self.duel_t += dt
            if self.duel_t >= DUEL_TIME * len(self.events):
                self.after_results()
        if self.cur().cpu and self.phase not in ("moving", "jump", "over", "duel"):
            self.cpu_update(dt)

    # ============================================================ 繪圖
    def draw(self):
        self.screen.fill(COL["bg"])
        getattr(self, "draw_" + self.scene)()
        for b in self.buttons:
            b.draw(self.screen, self.mouse)
        f = font(15, True)                    # 浮水印（每個畫面都有）
        w = f.size(WATERMARK)[0] + 26
        r = pygame.Rect(0, 0, w, 24)
        r.midbottom = (SW // 2, SH - 4) if self.scene in ("title", "rules") else (PANEL_X + 215, SH - 4)   # 對戰中放右下，不擋提示
        pygame.draw.rect(self.screen, (150, 22, 40), r, border_radius=12)
        text(self.screen, WATERMARK, r.center, 15, (255, 255, 255), "center", True)

    def draw_title(self):
        s = self.screen
        s.blit(self.title_bg(), (0, 0))
        panel = pygame.Surface((640, 640), pygame.SRCALPHA)       # 選單區半透明底
        pygame.draw.rect(panel, (22, 19, 34, 175), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (228, 255, 58, 90), panel.get_rect(), 2, border_radius=18)
        s.blit(panel, (SW // 2 - 320, 84))
        text(s, "逆轉金幣", (SW // 2, 150), 96, COL["yel"], "center", True)
        text(s, "Reverse Coin Battle｜逆転バリバリバース 2D 對戰", (SW // 2, 240), 26, COL["dim"], "center")
        text(s, "官方說明書 Ver.1.1.2 エキスパートルール・全 101 枚金幣", (SW // 2, 284), 22, COL["dim"], "center")
        text(s, WATERMARK, (SW // 2, 322), 22, (255, 107, 125), "center", True)
        self.draw_coin_at(Vector2(SW // 2 - 380, 150), "O", BY_ID["v1o-bbr"], 1.4, 0)
        self.draw_coin_at(Vector2(SW // 2 + 380, 150), "X", BY_ID["v1x-bbr"], 1.4, math.pi)

    def draw_rules(self):
        s = self.screen
        if getattr(self, "rule_imgs", None):
            n = math.ceil(len(self.rule_imgs) / 8)
            text(s, f"規則圖解（官方取扱説明書 Ver.1.1.2）　{self.rule_page + 1}／{n}", (40, 18), 32, COL["yel"], bold=True)
            imgs = self.rule_imgs[self.rule_page * 8:(self.rule_page + 1) * 8]
            cw, ch = 296, 322
            for i, im in enumerate(imgs):
                sc = min(cw / im.get_width(), ch / im.get_height())
                img = pygame.transform.smoothscale(im, (int(im.get_width() * sc), int(im.get_height() * sc)))
                x = 20 + (i % 4) * (cw + 14)
                y = 66 + (i // 4) * (ch + 10)
                s.blit(img, (x, y))
            return
        text(s, "規則說明（官方取扱説明書 Ver.1.1.2）", (60, 40), 40, COL["yel"], bold=True)
        lines = [
            "【賽前】先組隊：1～3 枚、同一隊不可重複，OX 合計 ≤ 15,000（メタ幣算 M 值）。再猜拳選陣營、擲金幣定先攻。",
            "【擊球】① 選金幣確定　② 滑鼠／←→ 決定方向（H 開關輔助線，關閉時用大三角箭頭）　③ 力量條　④ 精準度條",
            "　　　　精準度：中間綠區＝PERFECT 不偏；一離開就至少偏 5°，越靠邊越大，最邊緣左右各偏 70° 並帶弧線。",
            "【旋轉】出手前 Z 左旋／X 右旋（各 3 段）：金幣會轉、走弧線，撞到對手會傳遞旋轉並帶偏，撞邊框反彈角度改變；越強 PERFECT 綠區越窄。",
            "【翻轉】開關方向與正對面是リバースポット（黃色弧線）。力道夠強打中 → 彈起，落地正反面各 1/2。",
            "【防守方】彈起翻成對方顏色 → OUT；彈起仍是自己顏色 → OX 對決，守 ≥ 攻 セーフ（平手守方勝），原地重新鎖定。",
            "　　　　　被撞出界沒彈起 → 由攻擊方放回場上（離其他金幣 ≥ 1 枚，方向自由 Q／E）。",
            "【メタ幣】被打到彈起時中央核心會翻面，OX 對決用翻面後的數值（例：レオウ白 8000 → 黑面 4000）。",
            "【自滅】自己回合自己的金幣出界（含被自己撞出去的隊友）→ OUT；自爆翻成對方顏色 → OUT。",
            "　　　　自爆仍是自己顏色 → セーフ，原地重新鎖定。沒撞到任何金幣 → 無效攻擊。",
            "【場地】官方 A3 バリ場 297×420 mm（上 ORDER 白／下 XTREME 黑），金幣直徑 43 mm。",
            "【邊框】撞球檯式：垂直撞擊 ≥ 出界門檻（450，必定大於翻轉門檻 280）才飛出界，否則減速反彈；弱點撞牆 ≥ 280 也會彈起。",
            "【勝利】淘汰對手全部金幣。（程式開頭 OFFICIAL_RULES = False 可改回 isn_ver.1 自訂規則）",
        ]
        y = 110
        for ln in lines:
            text(s, ln, (60, y), 20, COL["text"] if ln.startswith("【") else COL["dim"])
            y += 42

    def draw_rps(self):
        s = self.screen
        p = self.players
        text(s, "猜拳決定陣營", (SW // 2, 110), 48, COL["yel"], "center", True)
        text(s, f"{p[0].name} 出 {self.rps_hands[0]}　vs　{p[1].name} 出 {self.rps_hands[1]}", (SW // 2, 220), 32,
             COL["text"], "center")
        w = p[self.rps_winner]
        text(s, f"{w.name} 獲勝！", (SW // 2, 290), 36, COL["green"], "center", True)
        if self.rps_stage == "pick":
            text(s, "電腦選擇中…" if w.cpu else f"{w.name} 請選擇陣營", (SW // 2, 380), 26, COL["dim"], "center")
        else:
            for i, pl in enumerate(p):
                text(s, f"{pl.name}：{CAMP_ZH[pl.camp]}", (SW // 2, 400 + i * 50), 30, COL["text"], "center")
            text(s, f"擲金幣結果：{CAMP_ZH[self.first_camp]} 先攻", (SW // 2, 540), 32, COL["yel"], "center", True)

    def draw_build(self):
        s = self.screen
        pl = self.players[self.build_idx]
        text(s, f"{pl.name} 組隊｜1～3 枚、不可重複，OX 合計 ≤ 15,000（メタ幣算 M 值；陣營之後猜拳決定）", (40, 24), 26, COL["yel"],
             bold=True)
        # 搜尋框
        box = pygame.Rect(40, 122, 300, 34)
        pygame.draw.rect(s, COL["panel2"], box, border_radius=8)
        pygame.draw.rect(s, COL["yel"] if self.q_active else COL["line"], box, 2, border_radius=8)
        if self.q:
            text(s, self.q + ("｜" if self.q_active and pygame.time.get_ticks() // 500 % 2 else ""), (box.x + 10, box.centery), 17,
                 COL["text"], "midleft")
        else:
            text(s, "點這裡搜尋名稱／中文名／商品" if not self.q_active else "輸入關鍵字…", (box.x + 10, box.centery), 15,
                 COL["dim"], "midleft")
        lst = self.filtered()
        rows_y, row_h, n_rows = 166, 34, 17
        self.scroll = min(self.scroll, max(0, len(lst) - n_rows))
        self.row_rects = []
        area = pygame.Rect(40, rows_y, 760, row_h * n_rows)
        pygame.draw.rect(s, COL["panel"], area, border_radius=10)
        for i, c in enumerate(lst[self.scroll:self.scroll + n_rows]):
            r = pygame.Rect(46, rows_y + i * row_h + 2, 748, row_h - 4)
            chosen = c.id in self.sel
            camp = c.main
            hov = r.collidepoint(self.mouse)
            if chosen or hov:
                pygame.draw.rect(s, (70, 56, 130) if chosen else COL["panel2"], r, border_radius=6)
            tag = pygame.Rect(r.x + 6, r.y + 4, 46, r.h - 8)
            pygame.draw.rect(s, RAR_COL[c.rarity], tag, border_radius=4)
            text(s, c.rarity, tag.center, 14, (255, 255, 255), "center", True)
            self.draw_coin_at(Vector2(r.x + 74, r.centery), camp, c, 14 / R, 0)
            text(s, c.jp, (r.x + 96, r.centery), 18, COL["text"], "midleft", True)
            text(s, c.zh, (r.x + 226, r.centery), 15, COL["dim"], "midleft")
            text(s, c.set, (r.x + 340, r.centery), 13, COL["dim"], "midleft")
            vals = f"白{c.o}／黑{c.x}" if c.meta else f"{c.o}"
            n = self.sel.count(c.id)
            text(s, vals, (r.x + 488, r.centery), 16, COL["yel"], "midleft", True)
            text(s, f"計 {'M' if c.meta else ''}{c.cost}", (r.right - 8, r.centery), 15, COL["dim"], "midright")
            self.row_rects.append((r, c))
        if not lst:
            text(s, "沒有符合的金幣，請放寬搜尋或分數範圍。", (60, rows_y + 20), 18, COL["dim"])
        text(s, f"符合 {len(lst)} / {len(COINS)} 枚｜分數＝組隊計分（メタ幣算 M 值）｜滾輪捲動｜點一下加入／移除",
             (40, area.bottom + 8), 15, COL["dim"])
        # 右側
        px = PANEL_X
        pygame.draw.rect(s, COL["panel"], (px, 70, 430, 700), border_radius=12)
        text(s, "隊伍（點清單加入／再點取消）", (px + 14, 82), 22, COL["text"], bold=True)
        self.slot_rects = []
        for k in range(3):
            r = pygame.Rect(px + 10, 116 + k * 74, 410, 66)
            pygame.draw.rect(s, COL["panel2"], r, border_radius=8)
            if k < len(self.sel):
                c = BY_ID[self.sel[k]]
                self.draw_coin_at(Vector2(r.x + 34, r.centery), c.main, c, 28 / R, 0)
                text(s, f"{c.rarity} {c.jp}", (r.x + 70, r.y + 10), 18, COL["text"], bold=True)
                text(s, f"白 {c.o}／黑 {c.x}　計 {'M' if c.meta else ''}{c.cost}", (r.x + 70, r.y + 36), 15, COL["dim"])
                text(s, "移除", (r.right - 26, r.centery), 15, COL["red"], "center")
                self.slot_rects.append((r, c.id))
            else:
                text(s, "（空）", r.center, 18, COL["dim"], "center")
        cost = self.build_cost()
        bar = pygame.Rect(px + 10, 346, 410, 20)
        pygame.draw.rect(s, COL["panel2"], bar, border_radius=6)
        fill = bar.copy()
        fill.w = int(bar.w * min(1, cost / BUDGET))
        pygame.draw.rect(s, COL["red"] if cost > BUDGET else COL["green"], fill, border_radius=6)
        text(s, f"OX 合計 {cost:,} / {BUDGET:,}", (px + 14, 322), 18, COL["red"] if cost > BUDGET else COL["text"],
             bold=True)
        text(s, f"{len(self.sel)} 枚", (px + 420, 322), 16, COL["yel"], "topright")

    # ------------------------------------------------------------ 對戰畫面
    def draw_coin_at(self, pos, camp, coin, scale=1.0, angle=0.0, squash=1.0, show_flipped=False, alpha=255,
                     spots=False):
        r = R * scale
        ring_white = (camp == "O") != show_flipped
        img = sprite(coin.id, "o" if ring_white else "x")
        if img is not None:
            k = 2 * r / SPRITE_COIN_D
            surf = pygame.transform.rotozoom(img, -math.degrees(angle), k)
            if abs(squash) < 0.999:
                w = max(1, int(surf.get_width() * abs(squash)))
                surf = pygame.transform.smoothscale(surf, (w, surf.get_height()))
            if alpha < 255:
                surf = surf.copy()
                surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(pos.x, pos.y)))
        else:
            self.draw_coin_fallback(pos, coin, r, scale, angle, squash, ring_white, alpha)
        if spots:
            box = pygame.Rect(pos.x - r - 5, pos.y - r - 5, 2 * r + 10, 2 * r + 10)
            for base in (angle, angle + math.pi):
                a0, a1 = -base - SPOT_HALF, -base + SPOT_HALF
                pygame.draw.arc(self.screen, COL["yel"], box, a0, a1, 3)

    def draw_coin_fallback(self, pos, coin, r, scale, angle, squash, ring_white, alpha):
        surf = pygame.Surface((int(r * 3), int(r * 3)), pygame.SRCALPHA)
        c = Vector2(surf.get_width() / 2, surf.get_height() / 2)
        rx = max(1, r * abs(squash))
        ring = COL["white"] if ring_white else COL["black"]
        edge = (150, 146, 168) if ring_white else (110, 104, 130)
        pygame.draw.ellipse(surf, ring, pygame.Rect(c.x - rx, c.y - r, 2 * rx, 2 * r))
        pygame.draw.ellipse(surf, edge, pygame.Rect(c.x - rx, c.y - r, 2 * rx, 2 * r), max(1, int(2 * scale)))
        ir = r * 0.6
        irx = ir * abs(squash)
        pygame.draw.ellipse(surf, char_color(coin.jp), pygame.Rect(c.x - irx, c.y - ir, 2 * irx, 2 * ir))
        if abs(squash) > 0.6:
            text(surf, coin.jp[:2], c, max(10, int(11 * scale)), (20, 20, 30), "center", True)
        u = Vector2(math.cos(angle), math.sin(angle))
        pygame.draw.circle(surf, (170, 170, 185), c + u * Vector2(rx, r).elementwise(), max(3, 5 * scale))
        if alpha < 255:
            surf.set_alpha(alpha)
        self.screen.blit(surf, surf.get_rect(center=(pos.x, pos.y)))

    def draw_table(self):
        s = self.screen
        outer = FIELD.inflate(2 * RAIL + 8, 2 * RAIL + 8)
        pygame.draw.rect(s, (74, 52, 36), outer, border_radius=14)              # 木框
        pygame.draw.rect(s, (110, 80, 54), outer, 2, border_radius=14)
        cush = FIELD.inflate(2 * RAIL, 2 * RAIL)
        pygame.draw.rect(s, (46, 40, 58), cush, border_radius=8)                 # 回彈墊
        pygame.draw.rect(s, (88, 80, 110), FIELD.inflate(6, 6), 3, border_radius=4)
        img = field_art()
        if img is not None:
            s.blit(img, FIELD)
        else:
            pygame.draw.rect(s, COL["field"], FIELD)
        for cx, cy in ((outer.left + 9, outer.top + 9), (outer.right - 9, outer.top + 9),
                       (outer.left + 9, outer.bottom - 9), (outer.right - 9, outer.bottom - 9)):
            pygame.draw.circle(s, (150, 120, 80), (cx, cy), 4)

    def draw_battle(self):
        s = self.screen
        self.draw_table()
        pl = self.cur()
        text(s, f"輪到：{pl.name}　{CAMP_ZH[pl.camp]}", (40, 18), 26,
             COL["white"] if pl.camp == "O" else COL["yel"], bold=True)

        aiming = self.phase in ("aim", "power", "accuracy")
        if aiming and self.selected:
            self.draw_aim_guide()
        for p in self.pieces:
            if not p.alive:
                continue
            squash, flipped, scale = 1.0, False, 1.0
            if self.phase == "jump" and p.unlocked:
                t = self.jump_t
                scale = 1 + 0.6 * math.sin(math.pi * t)
                squash = math.cos(t * 2 * math.pi) if p.flipped else math.cos(t * 4 * math.pi)
                flipped = p.flipped and t > 0.25
            self.draw_coin_at(p.pos, p.camp, p.coin, scale, p.angle, squash, flipped,
                              alpha=110 if p.out else 255, spots=aiming and p.team != self.turn)
            if abs(p.spin) > 1 and not p.out:            # 旋轉中：洋紅色光圈跟著轉
                rr = pygame.Rect(0, 0, 2 * R + 10, 2 * R + 10)
                rr.center = (int(p.pos.x), int(p.pos.y))
                a = -p.angle
                w = min(1.0, 0.3 + abs(p.spin) / 20)
                col = tuple(int(c * w + 30 * (1 - w)) for c in SPIN_COL)
                for k in (0, math.pi):
                    pygame.draw.arc(s, col, rr, a + k, a + k + 2.0, 4)
            arc_value(s, p.pos, p.value, p.camp)
            if p is self.selected and self.phase in ("select", "aim", "power", "accuracy"):
                pygame.draw.circle(s, COL["yel"], p.pos, R + 6, 2)
                if SPIN_ON and getattr(self, "spin_lvl", 0) and not self.cur().cpu:
                    self.draw_spin_arc(p.pos, self.spin_lvl)
        if self.phase == "select" and not self.cur().cpu:
            text(s, "點自己的金幣選擇，再點一次（或 Space）確定｜Tab 切換", (FIELD.centerx, FIELD.bottom + RAIL + 22), 18,
                 COL["dim"], "center")
        if self.phase == "place":
            p = self.place_queue[0]
            m = Vector2(self.mouse)
            if self.cur().cpu:
                text(s, "電腦正在安排回場位置…", (FIELD.centerx, FIELD.bottom + RAIL + 22), 18, COL["dim"], "center")
            else:
                ok = self.place_valid(m, p)
                self.draw_coin_at(m, p.camp, p.coin, 1.0, p.home_angle + self.place_rot, alpha=160)
                pygame.draw.circle(s, COL["green"] if ok else COL["red"], m, 2 * R, 2)
                text(s, f"攻擊方請安排 {p.coin.jp} 的回場位置（綠圈＝可放，Q／E 轉方向）", (FIELD.centerx, FIELD.bottom + RAIL + 22), 18,
                     COL["amber"], "center")
        if self.phase == "duel":
            self.draw_duel()
        # 倒數：每回合 18 秒（圓）＋全場剩餘
        if self.phase in ("select", "aim", "power", "accuracy", "place"):
            t = math.ceil(self.turn_t)
            c = (FIELD.left - 44, FIELD.top + 40)
            hurry = t <= 5
            pygame.draw.circle(s, (22, 20, 31), c, 34)
            pygame.draw.circle(s, COL["red"] if hurry else COL["yel"], c, 30)
            text(s, str(t), c, 30, (255, 255, 255) if hurry else (22, 20, 31), "center", True)
        if self.phase != "over" and hasattr(self, "match_t"):
            mt = math.ceil(self.match_t)
            label = f"全場 {mt // 60}:{mt % 60:02d}" if mt > 0 else "全場時間到"
            r = pygame.Rect(0, 0, 112, 26)
            r.center = (FIELD.left - 44, FIELD.top + 94)
            r.x = max(4, r.x)
            pygame.draw.rect(s, (192, 38, 58) if mt <= 60 else COL["panel"], r, border_radius=13)
            text(s, label, r.center, 14, COL["white"], "center", True)
        if self.phase == "over":
            box = pygame.Rect(FIELD.centerx - 300, 300, 600, 260)
            pygame.draw.rect(s, COL["panel"], box, border_radius=16)
            pygame.draw.rect(s, COL["yel"], box, 3, border_radius=16)
            msg = "平手！" if self.winner == -1 else f"{self.players[self.winner].name} 獲勝！"
            text(s, msg, (box.centerx, 380), 48, COL["yel"], "center", True)
            tr = getattr(self, "time_result", None)
            if tr:
                text(s, f"全場時間到｜開場 M 值合計 {tr[0]:,} vs {tr[1]:,}", (box.centerx, 432), 20, COL["text"], "center")
                text(s, "相同 → 平手" if tr[0] == tr[1] else "合計較少的一方獲勝", (box.centerx, 460), 18, COL["dim"], "center")
        self.draw_panel()

    def draw_duel(self):
        s = self.screen
        k = min(int(self.duel_t // DUEL_TIME), len(self.events) - 1)
        kind, att, dfn, survived = self.events[k]
        t = (self.duel_t - k * DUEL_TIME) / DUEL_TIME           # 0..1
        shade = pygame.Surface((FIELD.w, FIELD.h), pygame.SRCALPHA)
        shade.fill((10, 8, 18, 170))
        s.blit(shade, FIELD)
        box = pygame.Rect(0, 0, 470, 330)
        box.center = FIELD.center
        pygame.draw.rect(s, COL["panel"], box, border_radius=18)
        pygame.draw.rect(s, COL["yel"], box, 3, border_radius=18)
        title = "OX 對決" if kind == "duel" else "翻面！"
        text(s, title, (box.centerx, box.y + 32), 34, COL["yel"], "center", True)
        if len(self.events) > 1:
            text(s, f"{k + 1}/{len(self.events)}", (box.right - 18, box.y + 18), 15, COL["dim"], "topright")
        if kind == "duel":
            pop = min(1.0, t / 0.18)
            lx, rx, cy = box.x + 110, box.right - 110, box.y + 140
            self.draw_coin_at(Vector2(lx, cy), att.camp, att.coin, 1.55 * (0.6 + 0.4 * pop), att.home_angle)
            self.draw_coin_at(Vector2(rx, cy), dfn.camp, dfn.coin, 1.55 * (0.6 + 0.4 * pop), dfn.home_angle,
                              show_flipped=True)
            text(s, f"攻擊方｜{att.coin.jp}", (lx, cy + 66), 17, COL["text"], "center", True)
            text(s, f"防守方｜{dfn.coin.jp}" + ("（核心翻面）" if dfn.coin.meta else ""), (rx, cy + 66), 17,
                 COL["text"], "center", True)
            grow = min(1.0, max(0.0, (t - 0.12) / 0.3))
            text(s, str(int(att.value * grow)), (lx, cy + 100), 34, COL["yel"], "center", True)
            text(s, str(int(dfn.ox_after_pop * grow)), (rx, cy + 100), 34, COL["yel"], "center", True)
            if t > 0.45:
                sym = "≤" if dfn.ox_after_pop >= att.value else "＞"
                text(s, sym, (box.centerx, cy + 100), 40, COL["text"], "center", True)
                msg, col = (("防守方存活！", COL["green"]) if survived else ("防守方淘汰！", COL["red"]))
                note = "（平手守方勝）" if dfn.ox_after_pop == att.value else ""
                text(s, msg + note, (box.centerx, box.bottom - 32), 28, col, "center", True)
            else:
                text(s, "VS", (box.centerx, cy), 36, COL["text"], "center", True)
        else:
            cy = box.y + 150
            flipped_now = t > 0.35
            sq = math.cos(min(1.0, t / 0.35) * math.pi) if not flipped_now else -1
            self.draw_coin_at(Vector2(box.centerx, cy), dfn.camp, dfn.coin, 1.9, dfn.home_angle,
                              squash=sq if abs(sq) > 0.05 else 0.05, show_flipped=flipped_now)
            text(s, f"{dfn.coin.jp}（{dfn.value}）", (box.centerx, cy + 82), 20, COL["text"], "center", True)
            if flipped_now:
                text(s, "翻成對方顏色 → 淘汰！（不比 OX）", (box.centerx, box.bottom - 32), 24, COL["red"], "center",
                     True)

    def predict_path(self, p, aim, spin, speed):
        """依旋轉、摩擦模擬母球路線，回傳（折線點、撞到的金幣、撞擊位置、撞擊時速度方向）。"""
        pos, vel, w = Vector2(p.pos), Vector2(math.cos(aim), math.sin(aim)) * speed, spin
        pts, dt = [Vector2(pos)], 1 / 240
        others = [q for q in self.field_pieces() if q is not p]
        lo_x, hi_x, lo_y, hi_y = FIELD.left + R, FIELD.right - R, FIELD.top + R, FIELD.bottom - R
        for i in range(240 * 8):
            sp = vel.length()
            if sp < 3:
                break
            if w:
                k = CURL_K * w * dt
                vel = Vector2(vel.x - vel.y * k, vel.y + vel.x * k)
                d = SPIN_DECEL * dt
                w = 0.0 if abs(w) <= d else w - math.copysign(d, w)
            sp = vel.length()
            vel = vel * max(0.0, (sp - FRICTION * dt) / sp)
            pos += vel * dt
            if i % 6 == 0:
                pts.append(Vector2(pos))
            for q in others:
                if pos.distance_to(q.pos) < 2 * R:
                    pts.append(Vector2(pos))
                    return pts, q, pos, vel.normalize()
            if not (lo_x <= pos.x <= hi_x and lo_y <= pos.y <= hi_y):
                pos.x, pos.y = max(lo_x, min(hi_x, pos.x)), max(lo_y, min(hi_y, pos.y))
                pts.append(Vector2(pos))
                break
        return pts, None, pos, None

    def draw_aim_guide(self):
        s = self.screen
        p = self.selected
        u = Vector2(math.cos(self.aim), math.sin(self.aim))
        lvl = getattr(self, "spin_lvl", 0) if SPIN_ON else 0
        hit, best = None, 1e9
        for q in self.field_pieces():
            if q is p:
                continue
            f = p.pos - q.pos
            b = f.dot(u)
            c = f.dot(f) - (2 * R) ** 2
            disc = b * b - c
            if disc < 0:
                continue
            t = -b - math.sqrt(disc)
            if 0 < t < best:
                best, hit = t, q
        end = p.pos + u * (best if hit else 900)
        perp = Vector2(-u.y, u.x)

        def dotted(pts, col, w):
            """虛線圓點（往前流動）：輔助線、後拉線都用這個。"""
            r = max(3, int(w * 0.75) + 1)
            sp = r * 3.6
            nxt = (pygame.time.get_ticks() / 1000 * 90) % sp
            acc = 0.0
            for a, b in zip(pts, pts[1:]):
                a, b = Vector2(a), Vector2(b)
                L = a.distance_to(b)
                while nxt <= acc + L:
                    q = a.lerp(b, (nxt - acc) / L) if L else a
                    pygame.draw.circle(s, (0, 0, 0), q, r + 2)
                    pygame.draw.circle(s, col, q, r)
                    nxt += sp
                acc += L

        def bold_line(a, b, col, w):
            dotted([a, b], col, w)

        if self.guide and lvl:
            # 有旋轉：依目前力量（還沒決定時以 60% 估算）模擬會彎的路線
            pw = self.power if self.phase in ("aim", "power", "accuracy") and self.power > 0.05 else 0.6
            pts, hit, end, d = self.predict_path(p, self.aim, lvl * SPIN_STEP, VMIN + pw * (VMAX - VMIN))
            if len(pts) > 1:
                dotted([q for q in pts if q.distance_to(p.pos) > R + 4], AIM_COL, 4)
            if hit:
                u = d
        elif self.guide:
            bold_line(p.pos + u * (R + 4), end, AIM_COL, 3)
        if self.guide:
            if hit:
                pygame.draw.circle(s, (0, 0, 0), end, R + 2, 5)       # 母球撞擊位置（ghost）
                pygame.draw.circle(s, AIM_COL, end, R, 2)
                n = hit.pos - end
                if n.length():
                    n = n.normalize()
                    tgt = hit.pos + n * 100                            # 目標沿連心線前進
                    bold_line(hit.pos, tgt, TGT_COL, 4)
                    pygame.draw.circle(s, TGT_COL, tgt, 5)
                    cut = u - n * u.dot(n)                              # 母球沿切線分開（約 90°）
                    if cut.length() > 0.05:
                        bold_line(end, end + cut.normalize() * 80 * cut.length(), CUT_COL, 3)
        # 後拉橡皮筋：從金幣往拉的方向延伸，顏色依力量
        if self.phase == "aim" and self.power > 0.01:
            u0 = Vector2(math.cos(self.aim), math.sin(self.aim))
            L = R + self.power * PULL_MAX * 0.7
            col = COL["red"] if self.power > 0.85 else COL["amber"] if self.power > 0.5 else COL["green"]
            bold_line(p.pos - u0 * L, p.pos - u0 * (R * 0.9), col, 7)   # 圓點往發射方向流動
            text(s, f"{int(self.power * 100)}%", p.pos - u0 * (L + 18), 18, COL["white"], "center", True)
        # 三角形箭頭：輔助線開＝小；關＝大（只靠箭頭決定方向）
        u = Vector2(math.cos(self.aim), math.sin(self.aim))
        big = not self.guide
        L, half, gap = (8, 4, 13) if big else (8, 4, 6)           # 輔助線關閉時的箭頭再縮小 50%
        base = p.pos + u * (R + gap)
        if big:
            bold_line(p.pos + u * (R + 2), base, COL["yel"], 6)
        tri = [base + u * L, base + perp * half, base - perp * half]
        pygame.draw.polygon(s, (0, 0, 0), [base + u * (L + 3), base + perp * (half + 3) - u * 2, base - perp * (half + 3) - u * 2])
        pygame.draw.polygon(s, COL["yel"], tri)

    def draw_spin_arc(self, c, lvl):
        s = self.screen
        rr = R + 27
        a0 = pygame.time.get_ticks() / 1000 * 2.2 * lvl
        span = math.pi * 1.3
        pts = [c + Vector2(math.cos(a0 + span * i / 30 * (1 if lvl > 0 else -1)),
                           math.sin(a0 + span * i / 30 * (1 if lvl > 0 else -1))) * rr for i in range(31)]
        pygame.draw.lines(s, (0, 0, 0), False, pts, 7)
        pygame.draw.lines(s, SPIN_COL, False, pts, 4)
        end, prev = pts[-1], pts[-2]
        u = (end - prev).normalize()
        perp = Vector2(-u.y, u.x)
        pygame.draw.polygon(s, SPIN_COL, [end + u * 10, end + perp * 7, end - perp * 7])

    def draw_panel(self):
        s = self.screen
        px = PANEL_X
        pygame.draw.rect(s, COL["panel"], (px, 70, 430, 700), border_radius=12)
        y = 82
        for t in (1, 0):
            pl = self.players[t]
            col = COL["white"] if pl.camp == "O" else COL["dim"]
            mark = "＞ " if t == self.turn else "　 "
            text(s, f"{mark}{pl.name}｜{CAMP_ZH[pl.camp]}", (px + 14, y), 20, col, bold=True)
            y += 30
            for p in self.pieces:
                if p.team != t:
                    continue
                c = COL["text"] if p.alive else (90, 86, 104)
                st = "" if p.alive else "  淘汰"
                text(s, f"{p.coin.rarity} {p.coin.jp}  {p.value}{st}", (px + 30, y), 17, c)
                y += 24
            y += 8
        pygame.draw.line(s, COL["line"], (px + 10, y), (px + 420, y))
        # 力量條／精準度條
        y += 12
        self.draw_bars(px + 14, y)
        y += 178
        pygame.draw.line(s, COL["line"], (px + 10, y), (px + 420, y))
        y += 8
        text(s, "戰況紀錄", (px + 14, y), 17, COL["yel"], bold=True)
        y += 26
        f = font(15)
        rows = []
        for ln in self.log:
            col = COL["red"] if ln.startswith("淘汰") else COL["green"] if ln.startswith("存活") else COL["dim"]
            cur = ""
            for ch in ln:
                if f.size(cur + ch)[0] > 395:
                    rows.append((cur, col))
                    cur = "　"
                cur += ch
            rows.append((cur, col))
        for ln, col in rows[-int((760 - y) / 21):]:
            text(s, ln, (px + 14, y), 15, col)
            y += 21

    def draw_bars(self, x, y):
        s = self.screen
        w = 400
        ph = self.phase
        text(s, "力量", (x, y), 17, COL["text"], bold=True)
        bar = pygame.Rect(x + 50, y + 2, w - 60, 22)
        pygame.draw.rect(s, COL["panel2"], bar, border_radius=6)
        if ph in ("aim", "power", "accuracy", "moving", "jump"):
            f = bar.copy()
            f.w = int(bar.w * self.power)
            col = COL["red"] if self.power > 0.85 else COL["amber"] if self.power > 0.5 else COL["green"]
            pygame.draw.rect(s, col, f, border_radius=6)
            text(s, f"{int(self.power * 100)}%", bar.center, 15, (20, 20, 30), "center", True)
        y += 44
        text(s, "精準", (x, y), 17, COL["text"], bold=True)
        bar = pygame.Rect(x + 50, y + 2, w - 60, 22)
        pygame.draw.rect(s, COL["panel2"], bar, border_radius=6)
        mid = bar.centerx
        sweet = pygame.Rect(0, bar.y, max(2, int(bar.w * self.perf_zone(getattr(self, "spin_lvl", 0) if SPIN_ON else 0))), bar.h)
        sweet.centerx = mid
        pygame.draw.rect(s, COL["green"], sweet)
        pygame.draw.line(s, COL["text"], (mid, bar.y - 4), (mid, bar.bottom + 4), 2)
        if ph in ("accuracy", "moving", "jump"):
            mx = mid + self.acc * bar.w / 2
            pygame.draw.polygon(s, COL["yel"], [(mx, bar.y - 2), (mx - 7, bar.y - 12), (mx + 7, bar.y - 12)])
            pygame.draw.line(s, COL["yel"], (mx, bar.y), (mx, bar.bottom), 3)
        y += 44
        lvl = getattr(self, "spin_lvl", 0) if SPIN_ON else 0
        text(s, "旋轉", (x, y), 17, COL["text"], bold=True)
        if SPIN_ON:
            if self.spin_btns:
                self.spin_btns[0].rect.topleft = (x + 50, y - 4)
                self.spin_btns[1].rect.topleft = (x + 254, y - 4)
            text(s, spin_label(lvl), (x + 200, y + 11), 18, SPIN_COL if lvl else COL["dim"], "center", True)
        else:
            text(s, "關（經典玩法，開場畫面可切換）", (x + 50, y + 1), 16, COL["dim"])
        y += 32
        hint = {
            "select": "① 點自己的金幣，按住往後拉",
            "aim": "② 往反方向拉（越長越大力），放開發射｜↑↓←→",
            "power": "③ 放開發射",
            "accuracy": "④ 精準度：停在中間綠區＝PERFECT",
            "moving": "金幣滑行中…",
            "jump": "彈起翻轉判定中…",
            "duel": "OX 對決！（點擊／Space 跳過）",
            "place": "攻擊方安排回場位置",
            "over": "對戰結束",
        }.get(ph, "")
        if self.cur().cpu and ph not in ("moving", "jump", "over"):
            hint = "電腦思考中…"
        text(s, hint, (x, y), 16, COL["amber"])


def main():
    assert OUT_SPEED > UNLOCK_SPEED, "出界門檻必須大於翻轉門檻"
    Game().run()


if __name__ == "__main__":
    main()
