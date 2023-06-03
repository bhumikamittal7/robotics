#credits - santripta

from machine import Pin, SoftI2C, I2C
from picozero import Pot
import ssd1306
from time import sleep
import random

WIDTH = 128
HEIGHT = 64

POTENTIO_MIN = 0.003

POTENTIO_MAX = 0.999

PADDLE_DIMS = (8, 16)
BALL_DIMS = (5, 5)

OLED_ATTACH = 0
DELTA_TIME = 1/60

AI_SPEED = 2
AI_MISPREDICTFACTOR = 0 # 0.8
AI_REFLECT_MISPREDICTCHANCE = 0.1 # 0.15
AI_DECISIONDELAY = 0.2 # 0.15

PADDLE_SPEEDUP = 1.05
WALL_SPEEDUP = 1.001

PADDLE_COLLISION_DELAY = 0.2

paddle_collision_timer = 0

last_ai_decision = 0
ai_decision_timer = 0
score = (0, 0)

def sgn(x):
    return 1 if x >= 0 else -1

def remap(thing, minin, maxin, minout, maxout):
    return minout + ((thing - minin) / (maxin - minin)) * (maxout - minout)

def clamp(thing, minout, maxout):
    return max(minout, min(thing, maxout))

def oled_connect(sda):
    i2c = SoftI2C(sda = Pin(sda), scl = Pin(sda + 1))
    return ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

def reset_ball():
    yv = random.randint(-3, 3)
    while yv == 0:
        yv = random.randint(-3, 3)
    
    # The ball is placed at the center of the screen
    return ((WIDTH - BALL_DIMS[0]) // 2, (HEIGHT - BALL_DIMS[1]) // 2, 2, yv)

def rect_intersection(A, B, x_off = 0, y_off = 0):
    # no intersection if any of the widths or heights are 0
    if A[2] == 0 or A[3] == 0 or B[2] == 0 or B[3] == 0:
        return False
    
    # if A is completely to the right of B or B is completely to the right of A
    if A[0] + x_off > B[0] + B[2] or B[0] > A[0] + x_off + A[2]:
        return False
    
    # if A is completely below B or B is completely below A
    if A[1] + y_off > B[1] + B[3] or B[1] > A[1] + y_off + A[3]:
        return False
    
    return True
    
def update_ball(ball, paddles):
    global score, paddle_collision_timer
    
    xp, yp = ball[0], ball[1]
    hv, vv = ball[2], ball[3]
    
    ball_bb = (xp, yp, BALL_DIMS[0], BALL_DIMS[1])
    
    if paddle_collision_timer <= 0:
        for paddle in paddles:
            paddle_collision = False
            test_bb = (paddle[0], paddle[1], PADDLE_DIMS[0], PADDLE_DIMS[1])
                    
            if vv != 0 and rect_intersection(ball_bb, test_bb, 0, vv):
                paddle_collision = True
                while not rect_intersection(ball_bb, test_bb, 0, sgn(vv)):
                    yp += sgn(vv)
                    ball_bb = (xp, yp, BALL_DIMS[0], BALL_DIMS[1])
                vv *= -PADDLE_SPEEDUP
            
            if not paddle_collision and hv != 0 and rect_intersection(ball_bb, test_bb, hv):
                paddle_collision = True
                while not rect_intersection(ball_bb, test_bb, sgn(hv)):
                    xp += sgn(hv)
                    ball_bb = (xp, yp, BALL_DIMS[0], BALL_DIMS[1])
                hv *= -PADDLE_SPEEDUP
            
            if paddle_collision:
                paddle_collision_timer = PADDLE_COLLISION_DELAY
                return (xp, yp, hv, vv)
    
    reset = xp < 0 or xp >= WIDTH - BALL_DIMS[0]
    
    if xp < 0:
        score = (score[0], score[1] + 1)
    
    if xp >= WIDTH - BALL_DIMS[0]:
        score = (score[0] + 1, score[1])
        
    if reset:
        return reset_ball()
    
    if yp < 0:
        yp = 0
        vv *= -WALL_SPEEDUP
        return (xp, yp, hv, vv)
    
    if yp > HEIGHT - BALL_DIMS[1]:
        yp = HEIGHT - BALL_DIMS[1]
        vv *= -WALL_SPEEDUP
        return (xp, yp, hv, vv)
    
    return (round(xp + hv), round(yp + vv), hv, vv)

def update_ai(paddle, ball):
    global ai_decision_timer, last_ai_decision
    
    if ai_decision_timer <= 0:
        target = round(ball[1] - (PADDLE_DIMS[1] * (1 + random.uniform(-AI_MISPREDICTFACTOR, AI_MISPREDICTFACTOR)) // 2))
        
        if random.uniform(0, 1) <= AI_REFLECT_MISPREDICTCHANCE:
            target += sgn(ball[3]) * -1 * PADDLE_DIMS[1]

        diff = target - paddle[1]
        
        last_ai_decision = target
        ai_decision_timer = random.uniform(AI_DECISIONDELAY/2, AI_DECISIONDELAY)
        
        new_y = round(paddle[1] + sgn(diff) * min(abs(diff), AI_SPEED))
        
        new_y = clamp(new_y, 0, HEIGHT - PADDLE_DIMS[1])
        
        return (paddle[0], new_y)
    
    target = last_ai_decision
    diff = target - paddle[1]
    new_y = round(paddle[1] + sgn(diff) * min(abs(diff), AI_SPEED))
    new_y = clamp(new_y, 0, HEIGHT - PADDLE_DIMS[1])
    return (paddle[0], new_y)

def display_score(oled, score):
    oled.text(f"{score[0]} - {score[1]}", (WIDTH - 48) // 2, 0)

def display_paddles(oled, paddles):
    for paddle in paddles:
        oled.fill_rect(paddle[0], paddle[1], PADDLE_DIMS[0], PADDLE_DIMS[1], 1)

def display_ball(oled, ball):
    oled.fill_rect(ball[0], ball[1], BALL_DIMS[0], BALL_DIMS[1], 1)

oled = oled_connect(OLED_ATTACH)
oled.fill(0)
oled.show()
paddle_input = Pot(2)

pl_input = round(remap(paddle_input.value, POTENTIO_MIN, POTENTIO_MAX, 0, HEIGHT - PADDLE_DIMS[1]))

paddle_l = (0, pl_input)
paddle_r = (WIDTH - PADDLE_DIMS[0], (HEIGHT - PADDLE_DIMS[1])//2)

ball = reset_ball()

while True:
    display_paddles(oled, (paddle_l, paddle_r))
    display_ball(oled, ball)
    display_score(oled, score)
    
    oled.show()
    
    pl_input = round(remap(paddle_input.value, POTENTIO_MIN, POTENTIO_MAX, 0, HEIGHT - PADDLE_DIMS[1]))
    paddle_l = (0, pl_input)
    paddle_r = update_ai(paddle_r, ball)
    
    ball = update_ball(ball, (paddle_l, paddle_r))
    
    sleep(DELTA_TIME)
    ai_decision_timer -= DELTA_TIME
    paddle_collision_timer -= DELTA_TIME
    oled.fill(0)

oled.fill(0)
oled.show()