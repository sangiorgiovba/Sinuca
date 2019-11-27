import itertools
import math
import random
from enum import Enum

import numpy as np
import pygame
import zope.event

import ball
import config
import cue
import event
import graphics
import table_sprites
from ball import BallType
from collisions import check_if_ball_touches_balls


class Player(Enum):
    Player1 = 1
    Player2 = 2


class GameState:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.window_caption)
        event.set_allowed_events()
        zope.event.subscribers.append(self.game_event_handler)
        self.canvas = graphics.Canvas()
        self.fps_clock = pygame.time.Clock()

    def fps(self):
        return self.fps_clock.get_fps()

    def mark_one_frame(self):
        self.fps_clock.tick(config.fps_limit)

    def create_white_ball(self):
        self.white_ball = ball.BallSprite(0)
        ball_pos = config.white_ball_initial_pos
        while check_if_ball_touches_balls(ball_pos, 0, self.balls):
            ball_pos = [random.randint(int(config.table_margin + config.ball_radius + config.hole_radius),
                                       int(config.white_ball_initial_pos[0])),
                        random.randint(int(config.table_margin + config.ball_radius + config.hole_radius),
                                       int(config.resolution[1] - config.ball_radius - config.hole_radius))]
        self.white_ball.move_to(ball_pos)
        self.balls.add(self.white_ball)
        self.all_sprites.add(self.white_ball)

    def game_event_handler(self, event):
        if event.type == "POTTED":
            self.table_coloring.update(self)
            self.balls.remove(event.data)
            self.all_sprites.remove(event.data)
            self.potted.append(event.data.number)
        elif event.type == "COLLISION":
            if not self.white_ball_1st_hit_is_set:
                self.first_collision(event.data)

    def set_pool_balls(self):
        counter = [0, 0]
        coord_shift = np.array([math.sin(math.radians(60)) * config.ball_radius *
                                2, -config.ball_radius])
        initial_place = config.ball_starting_place_ratio * config.resolution

        self.create_white_ball()
        
        ball_placement_sequence = list(range(1, config.total_ball_num))
        random.shuffle(ball_placement_sequence)

        for i in ball_placement_sequence:
            ball_iteration = ball.BallSprite(i)
            ball_iteration.move_to(initial_place + coord_shift * counter)
            if counter[1] == counter[0]:
                counter[0] += 1
                counter[1] = -counter[0]
            else:
                counter[1] += 2
            self.balls.add(ball_iteration)

        self.all_sprites.add(self.balls)

    def start_pool(self):
        self.reset_state()
        self.generate_table()
        self.set_pool_balls()
        self.cue = cue.Cue(self.white_ball)
        self.all_sprites.add(self.cue)

    def reset_state(self):
      
        self.current_player = Player.Player1
        self.turn_ended = True
        self.white_ball_1st_hit_is_set = False
        self.potted = []
        self.balls = pygame.sprite.Group()
        self.holes = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.OrderedUpdates()
        self.turn_number = 0
        self.ball_assignment = None
        self.can_move_white_ball = True
        self.is_game_over = False
        self.potting_8ball = {Player.Player1: False, Player.Player2: False}
        self.table_sides = []

    def is_behind_line_break(self):
        
        return self.turn_number == 0

    def redraw_all(self, update=True):
        self.all_sprites.clear(self.canvas.surface, self.canvas.background)
        self.all_sprites.draw(self.canvas.surface)
        self.all_sprites.update(self)
        if update:
            pygame.display.flip()
        self.mark_one_frame()

    def all_not_moving(self):
        return_value = True
        for ball in self.balls:
            if np.count_nonzero(ball.ball.velocity) > 0:
                return_value = False
                break
        return return_value

    def generate_table(self):
        table_side_points = np.empty((1, 2))
        
        holes_x = [(config.table_margin, 1), (config.resolution[0] /
                                              2, 2), (config.resolution[0] - config.table_margin, 3)]
        holes_y = [(config.table_margin, 1),
                   (config.resolution[1] - config.table_margin, 2)]
       
        all_hole_positions = np.array(
            list(itertools.product(holes_y, holes_x)))
        all_hole_positions = np.fliplr(all_hole_positions)
        all_hole_positions = np.vstack(
            (all_hole_positions[:3], np.flipud(all_hole_positions[3:])))
        for hole_pos in all_hole_positions:
            self.holes.add(table_sprites.Hole(hole_pos[0][0], hole_pos[1][0]))
            
            if hole_pos[0][1] == 2:
               
                offset = config.middle_hole_offset
            else:
                offset = config.side_hole_offset
            if hole_pos[1][1] == 2:
                offset = np.flipud(offset) * [1, -1]
            if hole_pos[0][1] == 1:
                offset = np.flipud(offset) * [-1, 1]
            table_side_points = np.append(
                table_side_points, [hole_pos[0][0], hole_pos[1][0]] + offset, axis=0)
        
        table_side_points = np.delete(table_side_points, 0, 0)
        for num, point in enumerate(table_side_points[:-1]):
          
            if num % 4 != 1:
                self.table_sides.append(table_sprites.TableSide(
                    [point, table_side_points[num + 1]]))
        self.table_sides.append(table_sprites.TableSide(
            [table_side_points[-1], table_side_points[0]]))
        self.table_coloring = table_sprites.TableColoring(
            config.resolution, config.table_side_color, table_side_points)
        self.all_sprites.add(self.table_coloring)
        self.all_sprites.add(self.holes)
        graphics.add_separation_line(self.canvas)

    def game_over(self, p1_won):
        font = config.get_default_font(config.game_over_label_font_size)
        if p1_won:
            text = "PLAYER 1 WON!"
        else:
            text = "PLAYER 2 WON!"
        rendered_text = font.render(text, False, (255, 255, 255))
        self.canvas.surface.blit(rendered_text, (config.resolution - font.size(text)) / 2)
        pygame.display.flip()
        pygame.event.clear()
        paused = True
        while paused:
            event = pygame.event.wait()
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                paused = False
        self.is_game_over = True

    def turn_over(self, penalize):
        if not self.turn_ended:
            self.turn_ended = True
            self.turn_number += 1
            if self.current_player == Player.Player1:
                self.current_player = Player.Player2
            else:
                self.current_player = Player.Player1
        if penalize:
            self.can_move_white_ball = True

    def check_potted(self):
        self.can_move_white_ball = False 
        if 0 in self.potted:
            self.create_white_ball()
            self.cue.target_ball = self.white_ball
            self.potted.remove(0)
            self.turn_over(True)
        if 8 in self.potted:
            if self.potting_8ball[self.current_player]:
                self.game_over(self.current_player == Player.Player1)
            else:
                self.game_over(self.current_player != Player.Player1)

    def check_remaining(self):
     
        stripes_remaining = False
        solids_remaining = False
        for remaining_ball in self.balls:
            if remaining_ball.number != 0 and remaining_ball.number != 8:
                stripes_remaining = stripes_remaining or remaining_ball.ball_type == BallType.Striped
                solids_remaining = solids_remaining or not remaining_ball.ball_type == BallType.Striped
        ball_type_remaining = {BallType.Solid: solids_remaining, BallType.Striped: stripes_remaining}

       
        self.potting_8ball = {Player.Player1: not ball_type_remaining[self.ball_assignment[Player.Player1]],
                              Player.Player2: not ball_type_remaining[self.ball_assignment[Player.Player2]]}

    def first_collision(self, ball_combination):
        self.white_ball_1st_hit_is_set = True
        self.white_ball_1st_hit_8ball = ball_combination[0].number == 8 or ball_combination[1].number == 8
        if ball_combination[0].number == 0:
            self.white_ball_1st_hit_type = ball_combination[1].ball_type
        else:
            self.white_ball_1st_hit_type = ball_combination[0].ball_type

    def check_pool_rules(self):
        if self.ball_assignment is not None:
            self.check_remaining()
        self.check_potted()
        self.first_hit_rule()
        self.potted_ball_rules()
        self.on_next_hit()

    def on_next_hit(self):
        self.white_ball_1st_hit_is_set = False
        self.turn_ended = False
        self.potted = []

    def potted_ball_rules(self):
        if len(self.potted) > 0:
           
            potted_stripe_count = len([x for x in self.potted if x > 8])
            potted_solid_count = len([x for x in self.potted if x < 8])
            only_stripes_potted = potted_solid_count == 0 and potted_stripe_count > 0
            only_solids_potted = potted_stripe_count == 0 and potted_solid_count > 0

            if only_solids_potted or only_stripes_potted:
                selected_ball_type = BallType.Striped if only_stripes_potted else BallType.Solid
                if self.ball_assignment is None:
                    
                    other_player, = set(Player) - {self.current_player}
                    other_ball_type, = set(BallType) - {selected_ball_type}
                    self.ball_assignment = {self.current_player: selected_ball_type, other_player: other_ball_type}
                    self.potting_8ball = {self.current_player: False, other_player: False}
                elif self.ball_assignment[self.current_player] != selected_ball_type:
                    self.turn_over(False)
        else:
            self.turn_over(False)

    def first_hit_rule(self):
        
        if not self.white_ball_1st_hit_is_set:
            self.turn_over(True)
        elif self.ball_assignment is not None:
            if not self.white_ball_1st_hit_8ball and self.ball_assignment[
                self.current_player] != self.white_ball_1st_hit_type:
                self.turn_over(True)
           
            elif self.white_ball_1st_hit_8ball:
                self.turn_over(not self.potting_8ball[self.current_player])
