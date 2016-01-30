import sqlite3 as lite
import sys
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.graphics.texture import TextureRegion
from kivy.input.motionevent import MotionEvent
from kivy.properties import NumericProperty, ListProperty, DictProperty, ReferenceListProperty,\
    ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from array import array
from random import random
from math import pi
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.config import Config
import os
from kivy.core.audio.audio_sdl2 import SoundSDL2, Sound, SoundLoader

__author__ = 'Adrir'


class DatabaseConnection(object):
    database = 'db/bar.db'

    def get_data(self):
        con = None
        try:
            con = lite.connect(self.database)
            cursor = con.cursor()
            cursor.execute('SELECT * FROM PLAYERS LIMIT 1')
            return "Players: %s" % (cursor.fetchone()[1])

        except lite.Error, e:
            print "Error %s:" % e.args[0]
            sys.exit(1)

        finally:
            if con:
                con.close()


class FooBall(Image):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)
    rotation = NumericProperty(0)
    is_alive = NumericProperty(1)
    life_remaining = NumericProperty(10)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos
        self.rotation = Vector(self.velocity_x, self.velocity_y).angle(Vector(1, 1)) - 45

        if self.is_alive is 0:
            self.life_remaining -= 1


class TransparentFooBall(FooBall):
    alpha = NumericProperty(255)


class PointSprite(FooBall):
    rgb_color_value = NumericProperty(180)
    life = NumericProperty(10)

    def __init__(self, xPosition, yPosition, velocity_x, velocity_y, **kwargs):
        FooBall.__init__(self)

        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.texture = Texture.create(size=(1, 1))
        self.texture.blit_buffer(
            array('B', [self.rgb_color_value, self.rgb_color_value, self.rgb_color_value / 3,
                        self.rgb_color_value + 50]),
            colorfmt='rgba',
            bufferfmt='ubyte')
        self.pos = Vector(xPosition, yPosition)

        def move(self):
            FooBall.move(self)

            self.texture.blit_buffer(
                array('B', [self.rgb_color_value, self.rgb_color_value / 3, self.rgb_color_value / 3,
                    self.rgb_color_value]),
                colorfmt='rgba',
                bufferfmt='ubyte')


class FooAnimated(FooBall):
    frame = NumericProperty(0)

    def move(self):
        FooBall.move(self)

        self.frame += 1

        if self.frame > 25:
            self.frame = 1

        self.source = self.src + str(self.frame)


class FooRandom(FooBall):
    shield_radius = NumericProperty(360)
    shield_x = NumericProperty(10)
    shield_y = NumericProperty(10)
    default_transparency = NumericProperty(50)

    def move(self):
        FooBall.move(self)

        if self.texture is None:
            self.texture = Texture.create(size=(self.size[0], self.size[1]), colorfmt='rgba',bufferfmt='ubyte')

        buffer = []

        for x in range(self.size[0]):
            for y in range(self.size[1]):

                if ((x-self.shield_x)*(x-self.shield_x))\
                        +((y-self.shield_y)*(y-self.shield_y)) \
                        <= self.shield_radius:

                    for i in range(3):
                        buffer.append(int(random() * 255))
                    buffer.append(self.default_transparency)
                else:
                    for i in range(4):
                        buffer.append(0)

        # initialize the array with the buffer values
        self.texture.blit_buffer(array('B', buffer), colorfmt='rgba', bufferfmt='ubyte')


class FooGame(Widget):
    sounds = DictProperty({})
    missiles = ListProperty([])
    particles = []
    shield = ObjectProperty(None)
    city = ObjectProperty(None)

    def load(self):

        # Dictionary keys correspond to filenames
        for file in os.listdir("aud"):
            filename, extension = os.path.splitext(file)
            dictionary_key = filename
            self.sounds[dictionary_key] = SoundSDL2(source=(os.path.join("aud", file)))
            # self.sounds[dictionary_key] = SoundLoader.load("aud/"+file)

        Clock.schedule_interval(self.update, 1.0 / 60.0)
        Clock.schedule_interval(self.updateParticles, 1.0 / 30.0)

    def updateParticles(self, dt):
        for particle in self.particles:

            particle.life -= 1

            if (particle.rgb_color_value > 40):
                particle.rgb_color_value -= 30
            else:
                self.particles.remove(particle)
                self.remove_widget(particle)
                continue

            if particle.life < 1:
                self.particles.remove(particle)
                self.remove_widget(particle)
                continue

            if (particle.y < self.y) or (particle.top > self.top):
                self.particles.remove(particle)
                self.remove_widget(particle)
                continue

            if (particle.x < self.x) or (particle.x > self.width):
                self.particles.remove(particle)
                self.remove_widget(particle)
                continue

            particle.move()

    def update(self, dt):

        for missile in self.missiles:

            if missile.is_alive is 0 and missile.life_remaining < 1:
                self.missiles.remove(missile)
                self.remove_widget(missile)
                continue

            missile.move()

            if ((missile.x - self.center_x) * (missile.x - self.center_x)) + ((missile.y - self.center_y) * (missile.y - self.center_y)) <= 60*60:
                missile.src = "atlas://res/explosion/"
                missile.is_alive = 0
                missile.life_remaining = 25
                self.sounds['explosion'].play()

            #bounce ball off bottom or top
            if (missile.y < self.y) or (missile.top > self.top):
                missile.velocity_y *= -1
                self.sounds['missilelaunch'].play()

            if (missile.x < self.x) or ((missile.x + missile.width) > self.width):
                missile.velocity_x *= -1
                # self.sounds['missilelaunch'].stop()
                self.sounds['missilelaunch'].play()

        if (len(self.missiles) >= 2):
            for i in range(5):
                trail = PointSprite(
                    self.missiles[1].pos[0],
                    self.missiles[1].pos[1],
                    -(self.missiles[0].velocity_x * 2) + ((random() - 0.5) * 1.2),
                    -(self.missiles[0].velocity_y * 2) + ((random() - 0.5) * 1.2))
                self.add_widget(trail,1)
                self.particles.append(trail)


    def on_touch_move(self, touch):
        for ball in self.missiles:
            ball.velocity = (Vector(touch.pos) - Vector(touch.opos)) * 0.05

    def on_touch_down(self, touch):
        pass
        self.missiles[1].pos = Vector(touch.x,touch.y)

# Declare both screens


class MenuScreen(Screen):
    def safe_exit(self):
        sys.exit(0)


class HighScoresScreen(Screen):
    pass


class SplashScreen(Screen):
    pass

class PlayScreen(Screen):
    game = ObjectProperty(None)

class FooApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(HighScoresScreen(name='highscores'))
        sm.add_widget(PlayScreen(name='play'))
        return sm


if __name__ == '__main__':
    FooApp().run()