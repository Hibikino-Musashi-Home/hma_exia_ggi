#!/usr/bin/env python
# -*- coding: utf-8 -*-

#==================================================
#DoubleMetaphoneアルゴリズムにより音の近さを計算するサービスサーバ
#
#author: Tomohiro ONO
#==================================================

import rospy
import os
from metaphone import doublemetaphone as dmeta
from Levenshtein import distance
from common_pkg.srv import *

def handle_double_metaphone(req) :
  f = open(os.path.dirname(__file__) + '/command_list/' + req.file_name + '.txt', 'r')
  commands = f.readlines()

  command = {}
  for c in commands :
    c = c.replace('\n', '')
    command[c] = dmeta(c)[0]

  input_command = dmeta(req.input_text)[0]

  # レーベンシュタイン距離を計算
  command_ = {}
  for k, v in command.items() :
	  command_[str(k)] = int(distance(input_command, v))

  # 降順にソート（距離が短い順）
  command_ = sorted(command_.items(), key = lambda x: x[1])  

	# 出力用
  output_text = command_[0][0]

  distance_ = int(command_[0][1])

  print command_
  print '=> ', req.input_text, ' : ', output_text, distance_
  print "----------------------------"

  if distance_ >= req.allow_distance :
    output_text = "ERROR"
  
  f.close()
  return DoubleMetaphoneResponse(output_text, distance_)

def double_metaphone_server() :
    rospy.init_node('double_metaphone_server')
    s = rospy.Service('double_metaphone', DoubleMetaphone, handle_double_metaphone)
    print "Ready to Double Metaphone"
    rospy.spin()

if __name__ == "__main__" :
    double_metaphone_server()
