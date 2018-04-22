#coding: utf-8
# 'Breakout20180417' -> 'my_breakout.py'  (最終版)
# Open_AI_Gym対応Version　AI学習用（人間用は、'Breakout20180414F'が最終版）

import os
print(os.getcwd())                  # 現在のディレクトリを表示 

import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import numpy as np
import matplotlib.pyplot as plt

import gym
from gym import spaces, logger
from gym.utils import seeding


# グローバル変数の定義
SCREEN = Rect(0, 0, 400, 400)       # ゲームスクリーンの大きさ
GET_STATE_FRAME = 5                 # 状態s(t)を取得するフレーム
BANDWIDTH = 4                       # ニューラルネットへの入力チャンネル数
N_ACTIONS = 4                       # 行動の種類数（0:左移動,1:静止,2:右移動,3:ボール射出）
NOISE_PADDLE = 1                    # パドルとボールの反射における付加的な乱数角度[deg]

SNAPSHOT_SHOW = False


# バドルのクラス
class Paddle(pygame.sprite.Sprite):
    def __init__(self, filename):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.bottom = SCREEN.bottom - 20           # パドルのy座標
        self.dx = 10                                    # パドル速度
        
    def update(self, action):
        #self.rect.centerx = pygame.mouse.get_pos()[0]  # マウスのx座標をパドルのx座標に
        if action != 3:                                 # エージェント行動（パドル操作）
            self.rect.centerx += (action-1.0) * self.dx
        self.rect.clamp_ip(SCREEN)                      # ゲーム画面内のみで移動


# ボールのクラス
class Ball(pygame.sprite.Sprite):
    speed = 5                                           # ボール速度
    angle_left = 135                                    # ボール反射範囲
    angle_right = 45

    def __init__(self, filename, paddle, blocks, score):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.dx = self.dy = 0                           # ボールの速度初期値
        self.paddle = paddle                            # パドルへの参照
        self.blocks = blocks                            # ブロックグループへの参照
        self.update = self.start
        self.score = score
        self.hit = 0                                    # 連続でブロックを壊した回数
        self.done = False

    def start(self, action):
        self.done = False
        
        self.rect.centerx = self.paddle.rect.centerx    # ボールの初期位置(パドルの上)
        self.rect.bottom = self.paddle.rect.top
        
        #if pygame.mouse.get_pressed()[0] == 1:         # 左クリックでボール射出
        if action == 3:                                 # エージェント操作（ボール射出）
            self.dx = 0
            self.dy = -self.speed
            self.update = self.move

    def move(self, action):
        self.rect.centerx += self.dx
        self.rect.centery += self.dy
        
        # 壁との反射
        if self.rect.left < SCREEN.left:                # 左側
            self.rect.left = SCREEN.left
            self.dx = -self.dx                          # 速度を反転
        if self.rect.right > SCREEN.right:              # 右側
            self.rect.right = SCREEN.right
            self.dx = -self.dx
        if self.rect.top < SCREEN.top:                  # 上側
            self.rect.top = SCREEN.top
            self.dy = -self.dy
        
        # パドルとの反射(左端:135度方向, 右端:45度方向, それ以外:線形補間)
        if self.rect.colliderect(self.paddle.rect) and self.dy > 0:
            self.hit = 0                                # 連続ヒットを0に戻す
            (x1, y1) = (self.paddle.rect.left - self.rect.width, self.angle_left)
            (x2, y2) = (self.paddle.rect.right, self.angle_right)
            x = self.rect.left                          # ボールが当たった位置
            y = (float(y2-y1)/(x2-x1)) * (x - x1) + y1  # 線形補間
            noise = math.radians(np.random.normal(0, NOISE_PADDLE)) # 乱数要素
            angle = math.radians(y) + noise             # 反射角度 
            self.dx = self.speed * math.cos(angle)
            self.dy = -self.speed * math.sin(angle)
        
        # ボールを落とした場合
        if self.rect.top > SCREEN.bottom:
            self.update = self.start                    # ボールを初期状態に
            self.hit = 0
            self.score.add_score(-100)                  # スコア減点-100点
            self.done = True
        
        # ボールと衝突したブロックリストを取得
        blocks_collided = pygame.sprite.spritecollide(self, self.blocks, True)
        if blocks_collided:                             # 衝突ブロックがある場合
            oldrect = self.rect
            for block in blocks_collided:
                # ボールが左から衝突
                if oldrect.left < block.rect.left < oldrect.right < block.rect.right:
                    self.rect.right = block.rect.left
                    self.dx = -self.dx
                # ボールが右から衝突
                if block.rect.left < oldrect.left < block.rect.right < oldrect.right:
                    self.rect.left = block.rect.right
                    self.dx = -self.dx
                # ボールが上から衝突
                if oldrect.top < block.rect.top < oldrect.bottom < block.rect.bottom:
                    self.rect.bottom = block.rect.top
                    self.dy = -self.dy
                # ボールが下から衝突
                if block.rect.top < oldrect.top < block.rect.bottom < oldrect.bottom:
                    self.rect.top = block.rect.bottom
                    self.dy = -self.dy
                self.hit += 1                           # 衝突回数
                self.score.add_score(self.hit * 10)     # 衝突回数に応じてスコア加点


# ブロックのクラス
class Block(pygame.sprite.Sprite):
    def __init__(self, filename, x, y):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.left = SCREEN.left + x * self.rect.width
        self.rect.top = SCREEN.top + y * self.rect.height


# スコアのクラス
class Score():
    def __init__(self, x, y):
        self.sysfont = pygame.font.SysFont(None, 20)
        self.score = 0
        (self.x, self.y) = (x, y)
        
    def draw(self, screen):
        img = self.sysfont.render("SCORE:"+str(self.score), True, (255,255,250))
        screen.blit(img, (self.x, self.y))
        
    def add_score(self, x):
        self.score += x


# 環境のクラス
class Environment(gym.Env):
    def __init__(self):
        pygame.init()
        screen = pygame.display.set_mode(SCREEN.size)        
        self.screen = screen
        
        screen_width = SCREEN[2]-SCREEN[0]              # Observation spaceの定義
        screen_height = SCREEN[3]-SCREEN[1]
        self.observation_space = spaces.Box(low=0, high=255, shape=(screen_height,screen_width,3))
        self.action_space = spaces.Discrete(N_ACTIONS)  # Action spaceの定義
        
        self.seed()  
        
    def reset(self):        
        group = pygame.sprite.RenderUpdates()           # 描画用のスプライトグループ
        blocks = pygame.sprite.Group()                  # 衝突判定用のスプライトグループ
        Paddle.containers = group
        Ball.containers = group
        Block.containers = group, blocks
        paddle = Paddle("paddle.png")                   # パドルの作成
        
        # ブロックの作成(14*10)
        for x in range(1, 15):
            for y in range(1, 11):
                Block("block.png", x, y)

        score = Score(10, 10)                           # スコアを画面(10, 10)に表示
        ball=Ball("ball.png", paddle, blocks, score)    # ボールを作成
        clock = pygame.time.Clock()
        
        state = Observation()                           # 状態の取得
        
        self.current_score = 0
        
        self.group = group
        self.score = score
        self.clock = clock
        self.ball = ball
        self.done = False
        self.state = state

        return state.obs_band

    def one_step(self, action):                         # 1フレーム分の進行            
        group = self.group
        screen = self.screen
        score = self.score
        
        screen.fill((0,20,0))
        group.update(action)                            # 全てのスプライトグループを更新
        group.draw(screen)                              # 全てのスプライトグループを描画
        score.draw(screen)                              # スコアを描画
        
        for event in pygame.event.get():                # エスケープ
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()

        self.done = self.ball.done

    def step(self, action):                             # GET_STATE_FRAMEフレーム分の進行
        old_score = self.current_score                  # = 状態遷移
        for sloop in range(GET_STATE_FRAME):
            if self.ball.done == False:
                self.one_step(action)
                
        current_score = self.score.score                # 報酬計算
        reward = current_score-old_score
        self.current_score = current_score
        clipped_reward = np.sign(reward)
        
        state = self.state.getState(self.screen)        # 状態取得
        done = self.done
        
        return state, clipped_reward, done, {}
                
    def render(self, mode = 'human'):                   # ゲーム進捗画面の描画
        if mode == 'human':
            pygame.display.update()
            pygame.time.wait(30)
    
    
    def seed(self, seed=None):
        self.np_random = seeding.np_random(seed)
        seed1 = seeding.np_random(seed)
        return [seed1]
    
    
    def close():
        pass
    

# 状態s(t)観測（画面取得）クラス
class Observation():
    def __init__(self):                                     # 初期化
        self.snapshot_resize = 84                           # スナップショットのリサイズ[pixel]
        #self.initial_skip = 0                       　　　　# スナップショットを最初にスキップするフレーム数        
        
        self.obs_band = np.zeros((BANDWIDTH,self.snapshot_resize,self.snapshot_resize),dtype=np.uint8)
                                                            # ニューラルネット入力の初期化

    # スクリーンショットを取得し、リサイズ後、NTSC 係数による加重平均法でグレースケールに変換
    def getSnapshot(self, screen):
        shot = pygame.surfarray.array3d(pygame.transform.scale(screen,(self.snapshot_resize,self.snapshot_resize)))
        shot = (shot[:,:,0]*0.298 + shot[:,:,1]*0.587 + shot[:,:,2]*0.114).T
        return np.array(shot, dtype=np.uint8)
    
    def getState(self, screen):                             # 状態（画面）取得                   
        obs = self.getSnapshot(screen) 

        self.obs_band = np.roll(self.obs_band, 1, axis=0)
        self.obs_band[0] = obs

        if SNAPSHOT_SHOW == True:                           # スクリーンショット表示
            #print(' Screen at {0}'.format(int(counter/FRAME_SKIP)))
            for i in range(BANDWIDTH):
                plt.imshow(self.obs_band[i], cmap='gray')
                plt.show()
                plt.close()
                
        return self.obs_band