#!/usr/bin/env python3

import numpy as np
import sys
import random as rnd
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


Model = np.zeros(1)
Model_fold = np.zeros(1)
BData = np.load('behavior_data.npy')

def s_AI(hand, deck):
	can = can_put(hand, deck)
	fold = not any(can)
	coefF = np.asarray([1, -0.5, 0.5, -0.5])
	coef = np.asarray([1, 1, -0.5, -0.5])
	if fold:
		penalty = {}
		for i in range(52):
			if not hand[i]:
				penalty[i] = np.inf
				continue			
			col = i // 13
			val = i % 13
			# sum(num), dist, recent, damage
			vec = np.zeros(4)
			if val < 6:
				for j in range(0, val+1):
					if hand[col*13+j]:
						vec[0] += j
					else:
						vec[3] += j
				for j in range(val+1, 6):
					if deck[col*13+j]:
						vec[1] = j - val
						if col*13+j in Last3:
							vec[2] = j - val
						break
			else:
				for j in range(val, 12):
					if hand[col*13+j]:
						vec[0] += j
					else:
						vec[3] += j
				for j in range(7, val):
					if deck[col*13+j]:
						vec[1] = j - val
						if col*13+j in Last3:
							vec[2] = j - val
						break
			penalty[i] = coefF@vec
		card = min(penalty, key=penalty.get)
		# print("[Debug]", penalty)
		return card
	else:
		if hand[6]:
			return 6
		gain = {}
		for i in range(52):
			if not can[i]:
				gain[i] = -np.inf
				continue
			
			col = i // 13
			val = i % 13
			# num, potential/dist, damage, recent damge, 
			vec = np.zeros(4)
			vec[0] = val
			if val < 6:
				for j in range(0, val):
					if hand[col*13+j]:
						vec[1] += j / (val - j)
					else:
						vec[2] += j
					if i+1 in Last3:
						vec[3] += j
			else:
				for j in range(val+1, 12):
					if hand[col*13+j]:
						vec[1] += j / (j - val)
					else:
						vec[2] += j
					if i-1 in Last3:
						vec[3] += j
			gain[i] = coef@vec
		card = max(gain, key=gain.get)
		# print("[Debug]", penalty)
		return card
		
def s_AI2(hand, deck):
	can = can_put(hand, deck)
	fold = not any(can)
	vec = np.asarray([float(x) for x in hand]+[float(x) for x in deck])

	can_vec = np.asarray([float(x) for x in can])
	if fold:
		probf = vec@Model_fold
		res = np.argmax(probf*can_vec)
	else:
		prob = vec@Model
		res = np.argmax(prob*can_vec)
	# print("[DEBUG]", res)
	if can[res]:
		# print("[DEBUG]smartboi")
		return res
	return hand.index(True) if fold else can.index(True)

def logBehavior(p, card, fold):
	Behavior[p].append([fold, card]+OnHand[p][:]+Deck[:])


def processBehavior(winn, weight):
	global BData
	global Model_fold
	global Model
	if winn is not None:
		BData = np.concatenate((BData, [[weight]+x for x in Behavior[winn]]), axis=0)
	# train model
	data1 = []
	data2 = []
	y1 = []
	y2 = []
	for x in BData:
		loop = 5
		# score fold card own[52] deck[52]
		score, fold, card = x[0:3]
		vec = x[3:]
		if score > 0:
			loop -= score//10
		loop = max(0, loop)
		for i in range(loop):		
			if fold == 1:
				data1.append(vec)
				y1.append([float(t==card) for t in range(52)])
			else:
				data2.append(vec)
				y2.append([float(t==card) for t in range(52)])

	Model_fold, res, rnk, sing = np.linalg.lstsq(data1, y1, rcond=None)
	Model, res, rnk, sing = np.linalg.lstsq(data2, y2, rcond=None)





rnd.seed(datetime.now())
while True:
	init()
	processBehavior(None, 0)
	# main loop
	while actions < 52:
			# print(current)
			pcard = -1
			pfold = not any(can_put(OnHand[current], Deck))
			if current == ppl[0]:
				print("[Game] Deck:")
				print_set(Deck)
				print("[Game] Your cards:")
				print_set(OnHand[current])#, highlight=color.YELLOW)
				while True:
					pinput = input("[Game] PLEASE ENTER [SHDC][A-K] or [*]: ")
					if '*' in pinput:
						# auto complete
						pcard = s_AI(OnHand[current], Deck)
						if '**' in pinput:
							print("[Suggestion] {} {}".format(header[pcard//13], letters[pcard%13]))
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

np.save('behavior_data.npy', BData)
print("[Data] Behavior data is saved to behavior_data.npy. N = {}".format(len(BData)))


# print([int(x) for x in Behavior['Player'][0]])
