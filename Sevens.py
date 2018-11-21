#!/usr/bin/env python3

import numpy as np
import sys
import random as rnd
import math
from datetime import datetime


OnHand = {}
Folded = {}
Deck = []
Last3 = []
Behavior = {}
current = ""
actions = 0

Player = 'Player'
ppl = (Player, 'Opponent 1', 'Opponent 2', 'Opponent 3')
suitdict = {"S":0, "H":1, "D":2, "C":3}
letters = ["A"]+[str(i) for i in range(2,11)]+["J", "Q", "K"]
header = ("Spade", "Heart", "Diamond", "Club")

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


def init():
	global OnHand
	global Deck
	global Folded
	global Behavior
	global current
	global actions
	global Last3

	for x in ppl:
		OnHand[x] = [False]*52
		Folded[x] = 0
		Behavior[x] = []
	got = {recvr:0 for recvr in ppl}
	for i in range(52):
		recvr = ppl[rnd.randint(0, 3)]
		while got[recvr] == 13:
			recvr = ppl[rnd.randint(0, 3)]
		OnHand[recvr][i] = True
		got[recvr] += 1
		# Spade 7
		if i == 6:
			current = recvr
			print("[Game]", recvr, "is to serve.")
	Deck = [False]*52
	Last3 = [-1]*3
	actions = 0

def parse_input(msg):
	if msg[0] not in "SsHhDdCc":
		return (-1, "[Alert] Unrecognized suid \"{}\".".format(msg[0])) 
	suit = suitdict[msg[0].upper()]
	if len(msg)<=1 or not msg[1:].strip():
		return (-1, "[Alert] Unable to comprehend number.") 
	msg = msg[1:].strip()
	if msg[0] in "AaJjQqKk":
		num = letters.index(msg[0].upper())
	else:
		try:
			num = int(msg)-1
		except ValueError:
			return (-1, "[Alert] Unable to comprehend number.") 
	return (suit*13+num, None)

def can_put(hand, deck):
	if not deck[6]:
		return 	[i==6 and hand[6] for i in range(52)]	
	acc = [False]*52
	for s in range(4):
		foundL = False
		foundR = False
		for i in range(8):
			if not foundL and (i==6 or deck[s*13+i+1]):
				acc[s*13+i] = hand[s*13+i]
				foundL = True
			if not foundR and deck[s*13+11-i]:
				acc[s*13+12-i] = hand[s*13+12-i]
				foundR = True
	return acc

def print_set(sset, end='\n', highlight=''):
	if highlight:
		acc = can_put(sset, Deck)
	for i in range(4):
		print(header[i].ljust(10, ' '), end='')
		for j in range(0,13):
			head = ""
			body = ""
			tail = ""
			if highlight and acc[i*13+j]:
				head = highlight
				tail = color.END
			body = (letters[j] if sset[i*13+j] else '-').ljust(3, ' ')
			print(head+body+tail,end='')
		print("")
	print("", end=end)



try:
	md = np.load('coefs.npy')
	coefF = md[0]
	coef = md[1]
except FileNotFoundError:
	print("[Data] coefs.npy not found. creating...")
	coefF = np.asarray([1, -0.5, 0.3, -0.5])
	coef = np.asarray([0, 1, -0.3, -0.1])


def decode(hand, deck, i, last3, fold):
	col = i // 13
	val = i % 13
	hsuit = hand[col*13:col*13+13]
	dsuit = deck[col*13:col*13+13]
	recent = []
	for x in last3:
		if x // 13 == col:
			recent.append(x%13)

	if fold:
		# model: (total penalty) - dist + recent_dist - damage
		penalty, dist, recent_dist, damage = [0, 0, 0, 0]
		# TODO redefine dist: how many 'unseen' cards between this card and the closest on deck
		if val < 6:
			for j in range(0, val+1):
				if hsuit[j]:
					penalty += j
				else:
					damage += j
			for j in range(val+1, 7):				
				if dsuit[j]:
					# dist = j - val
					if j in recent:
						recent_dist = dist
					break
				elif not hsuit[j]:
					dist += 1
				if j==6:
					# not even 7 is on deck
					dist += 1
					recent_dist = 0
		else:
			for j in range(val, 13):
				if hsuit[j]:
					penalty += j
				else:
					damage += j
			for j in range(6, val)[::-1]:
				if dsuit[j]:
					# dist = val - j
					if j in recent:
						recent_dist = dist
					break
				elif not hsuit[j]:
					dist += 1
				if j==6:
					# not even 7 is on deck
					dist = val - 6 + 1
					recent_dist = 0
		return np.asarray([penalty, dist, recent_dist, damage])
	else:
		# model: gain + potential_gain/dist - op gain - recent op gain
		gain, sub_gain, op_gain, recent_gain = [0, 0, 0, 0]
		gain = val
		if val <= 6:
			for j in range(0, val):
				if hsuit[j]:
					op_gain *= 0.5
					recent_gain *= 0.5
					# ^ this is because op_gain will influence val less now
					sub_gain += (j / math.sqrt(val - j))
				else:
					op_gain += j
					if val+1 in recent:
						recent_gain += j
		if val >= 6:
			for j in range(val+1, 13)[::-1]:
				if hsuit[j]:
					op_gain *= 0.5
					recent_gain *= 0.5
					# ^ this is because op_gain will influence val less now
					sub_gain += (j / math.sqrt(j - val))
				else:
					op_gain += j
					if val-1 in recent:
						recent_gain += j
				
		return np.asarray([gain, sub_gain, op_gain, recent_gain])


def s_AI(hand, deck):
	can = can_put(hand, deck)
	fold = not any(can)
	# coefF = np.asarray([1, -0.5, 0.3, -0.5])
	# coef = np.asarray([1, 1, -0.5, -0.5])	
	if fold:
		penalty = {}
		for i in range(52):
			if hand[i]:
				vec = decode(hand, deck, i, Last3, fold)
				penalty[i] = coefF@vec
			else:
				penalty[i] = np.inf
		card = min(penalty, key=penalty.get)
		return card
	else:
		if hand[6]:
			return 6
		gain = {}
		for i in range(52):
			if can[i]:
				vec = decode(hand, deck, i, Last3, fold)
				gain[i] = coef@vec
			else:
				gain[i] = -np.inf
		card = max(gain, key=gain.get)
		return card


def logBehavior(p, card, fold):
	# fixed bug: Last3 was empty for the first action
	Behavior[p].append([fold, card]+Last3[:]+OnHand[p][:]+Deck[:])

def norm(v):
	a = np.linalg.norm(v)
	if a <= 0:
		return v
	return v / a

def gradient(x, y, w):
	dot = x@w
	return 2*(np.arctan(dot)-y)/(1+dot**2)*x

def processBehavior(winn, weight):
	global coefF
	global coef
	if winn is None:
		return

	ita = 0.1
	delta_coefF = np.zeros(4)
	delta_coef = np.zeros(4)

	# train model	
	for x in Behavior[winn]:
		loop = 5
		# score fold card vec[4]
		score, fold, card = x[0:3]
		last3 = x[3:6]
		hand = x[6:58]
		deck = x[58:]
		
		if score > 13:
			loop = 1
		elif score > 0:
			loop = 2

		while loop > 0:
			loop -= 1		
			if fold == 1:
				tmp_y = []
				for j in range(52):
					if hand[j]:
						# maximum 13 additions
						vec = decode(hand, deck, j, last3, True)
						delta_coefF += gradient(vec, float(j==card), coefF)
			else:
				tmp_y = []
				can = can_put(hand, deck)
				for j in range(52):
					if can[j]:
						# maximum 8 additions
						vec = decode(hand, deck, j, last3, False)
						delta_coef += gradient(vec, float(j==card), coef)
	
	coefF = coefF - ita*norm(delta_coefF)
	coef = coef - ita*norm(delta_coef)
	# print(delta_coefF, delta_coef)





rnd.seed(datetime.now())
processBehavior(None, 0)
while True:
	init()	
	# main loop
	while actions < 52:
			# print(current)
			pcard = -1
			can = can_put(OnHand[current], Deck)
			pfold = not any(can)
			if current == ppl[0]:
				print("[Game] Deck:")
				print_set(Deck)
				print("[Game] Your cards:")
				print_set(OnHand[current], highlight=color.YELLOW)
				while True:
					pinput = input("[Game] PLEASE ENTER [SHDC][A-K] or [*]: ")
					if '*' in pinput:
						# auto complete
						pcard = s_AI(OnHand[current], Deck)
						if '**' in pinput:
							print("[Suggestion] {} {} {}".format("(Fold)" if pfold else "(Put)", header[pcard//13], letters[pcard%13]))
							continue
						break
					pcard, err = parse_input(pinput.lstrip())
					if err:
						print(err)
						continue					
					if not OnHand[current][pcard]:
						print("[Alert] You don't have this card!", pcard)
					elif not pfold and (pcard%13 > 6 and not Deck[pcard-1] or pcard%13 < 6 and not Deck[pcard+1]):
						print("[Alert] You can't put this card now!", pcard)
					elif OnHand[current][6] and pcard != 6:
						print("[Alert] Please put Spade 7 first.")
					else: 
						break
			else:
				pcard = s_AI(OnHand[current], Deck)

			logBehavior(current, pcard, pfold)			
			OnHand[current][pcard] = False
			Deck[pcard] = not pfold
			if pfold:
				Folded[current] += (pcard%13+1)
			else:
				if len(Last3) == 3:
					del Last3[0]
				Last3.append(pcard)
			actions += 1

			print(current, "FOLDED" if pfold else "PUT {} {}.".format(header[pcard//13], letters[pcard%13]))
			# print(current, ("FOLDED" if pfold else "PUT") + " {} {}.".format(header[pcard//13], letters[pcard%13]))

			current = ppl[(ppl.index(current)+1)%4]
	print("[Game] Game Over.")
	print("[Game] Penalty:")
	print(ppl[0].ljust(15, ' ')+ppl[1].ljust(15, ' ')+ppl[2].ljust(15, ' ')+ppl[3].ljust(15, ' '))
	print(str(Folded[ppl[0]]).ljust(15, ' ')+str(Folded[ppl[1]]).ljust(15, ' ')+\
		str(Folded[ppl[2]]).ljust(15, ' ')+str(Folded[ppl[3]]).ljust(15, ' '))
	winner = min(Folded, key=Folded.get)
	processBehavior(Player, Folded[Player]-Folded[winner])
	if winner != Player:	
		processBehavior(winner, Folded[winner])
	if input("[Game] Another game ? [Y/N]")[0].upper() != "Y":
		break 

np.save('coefs.npy', [coefF, coef])
print("[Data] Behavior data is saved to coefs.npy.", coefF, coef)


# print([int(x) for x in Behavior['Player'][0]])
