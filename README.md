# Sevens
A small game with adaptive opponents.
## How to play
Tested on Ubuntu 18.04 with python 3.7.1 installed.

Execute `Sevens.py` to start the game. Input format is `X Y` or `XY` where `X` is one of `S,H,D,C` which stands for `Spade, Heart, Diamond, Club` respectively, and Y is one of `1~13` or `A,J,Q,K`. Entering `*` will result in the game choosing a card for you, while `**` will have the game give you a suggestion. Available input cards will be shown in yellow (this does not work in Windows) for better decision.

## How it works (decisions)
Detailed explanation of the following functions 
```python
def decode(hand, deck, i, last3, fold)
def s_AI(hand, deck)
```
The program will calculate a score for each option of cards for each possible scenario (different meanning for folding and not folding). Decision on which card to fold/put on deck is made based on these values.

Suppose the cards an opponent has in hand is represented by the array `Hand[52]` and the cards on the table are represented by `Deck[52]`, the last 3 cards put on the table are in `last3[3]`. Let's consider two scenarios
##### Scenario 1 : `Hand` does not contain available cards.
In this case, we need to fold a card. We assume the following model for the penalty of folding a card
```
Total Penalty = a0*folded - a1*dist + a2*recent_dist - a3*damage
```
We calculate four values for each card on hand:
- `folded`: a value that specify how much points is folded, including points of cards destined to be folded should we choose to fold the current card. For example, folding `Spade 2` while holding `Spade A & 2` gives a value of `3`.
- `dist`: amount of opponents' cards between this card and the closest card on deck. The purpose of this is to reduce penalty for cards that are far away from the established sequence on deck, which is less hopeful to be available soon. For example, if the cards on deck are `Spade 7, 6, 5` and on hand `Spade A, 3` then folding `Spade A` yields a value of `2`.
- `recent_dist`: this value is to penalize the previous one if the sequence is moving toward the card we chose to fold. For example, assume same condition as in `dist`, but `Spade 5` is one of the latest 3 cards put on deck, then folding `Spade A` yields a value of `2`. combining with values `a1 > a2` gives a meaningful tradeoff.
- `damage`: damage to others. Suppose we have `Spade A, 3` then folding `Spade 3` yields `2`

As for `(a0, a1, a2, a3)`, we assume an initial model of `(1, 0.5, 0.3, 0.5)`. The model is updated (using behavior data from the Player or another winner) after each round. See [How it works (training and improving)](#how-it-works-training-and-improving)

The functions basically checks which card on hand has the least total penalty and outputs the card.
##### Scenario 2 : `Hand` does contain available cards to put.
In this case, we need to put a card. We assume the following model for the gain of putting a card
```
Total Gain = b0*gain + b1*potential_gain/sqrt(dist) - b2*op_gain - b3*recent_op_gain
```
We calculate four values for each card on hand:
- `gain`: the value of the card being put on deck.
- `potential_gain/sqrt(dist)`: sum of the following value for each cards being blocked by the current card: value of blocked card, divided by square-rooted distance between blocked and blocking card. The purpose of this is to encourage putting out cards that has many pending cards behind it. For example, if the cards on hand are `Spade 9, Q, K` then putting `Spade 9` yields a value of `12/1.732 + 13/2 = 13.43`.
- `op_gain`: potential gain for opponents assuming worst case where all subsequent cards are not folded. For example, if hand contains `Spade 8,10,Q`, then putting `Spade 8` yields `9 + (11 + 13/2)/2 = 17.5`. Note that `K` is halved twice and J is halved once since `K` is more relevant to `10,Q` than `8` and `J` more to `10` than `8`.
- `recent_op_gain`: this value further panalizes the direction where the sequence is going, so as to discourage putting cards that way. For example, if `Spade 8` is in `last3`, and `hand` contains `Spade 9, J`, then putting `Spade 9` will yield `10 + (12 + 13/2)/2 = 22.5` for this value.    

As for `(b0, b1, b2, b3)`, we assume an initial model of `(1, 0.5, 0.5, 0.3)`. The model is updated (using behavior data from the Player or another winner) after each round. See [How it works (training and improving)](#how-it-works-training-and-improving)

The functions basically checks which card on hand is available and has the most total gain and outputs the card.
## How it works (training and improving)
Detailed explanation of the following functions 
```python
def logBehavior(p, card, fold, can)
def processBehavior(winn, weight)	
```
##### logging
After each round, we want to update our model of folding & putting. The data comes from the Player's input as well as the winner's if one of the bots have beaten the Player. Each move is remembered by the program via the function `logBehavior`
```python
def logBehavior(p, card, fold, can):
  Behavior[p].append([fold, card]+Last3[:]+OnHand[p][:]+Deck[:])
```
- `fold`: whether it's a fold.
- `card`: which card is folded/put.
- `Last3`: Latest 3 cards put on deck.
- `OnHand[p]`: what cards are on p's hand.
- `Deck[]`: what cards are on deck.

After each round, the data is thrown into `processBehavior` with parameter `weight`. This is interpreted by the function as
```python
...
loop = 5
if weight > 13:
  loop = 1
elif weight > 0:
  loop = 3
...
```

which essentially states that more weight is less important. The following is the weights currently used
```python
processBehavior(Player, Folded[Player]-Folded[winner])
	if winner != Player:	
		processBehavior(winner, Folded[winner])
```

##### training
