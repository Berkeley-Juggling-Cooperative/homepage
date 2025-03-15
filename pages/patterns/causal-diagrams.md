<!--
.. title: How we create Causal Diagrams
.. slug: causal-diagrams
.. date: 2025-03-08 08:04:37 UTC-08:00
.. tags: 
.. category: patterns
.. link: 
.. description: How we create Causal Diagrams
.. type: text
-->

We wrote our own extension for [Nikola](https://getnikola.com), our
static web page generator, to generate Causal Diagrams.

The basics are taken from [this article](https://jugglingedge.com/help/causaldiagrams.php).

Currently, the generator can handle the following syntax:

# Simple diagram

    {{% raw %}}
    {{% causal_diagram %}}
    3p 3 3 3 3p 3 3 3
    3p 3 3 3 3p 3 3 3
    {{% /causal_diagram %}}
    {{% /raw %}}

results in:

{{% causal_diagram %}}
3p 3 3 3 3p 3 3 3
3p 3 3 3 3p 3 3 3
{{% /causal_diagram %}}

The jugglers are automatically labeled "A", "B", etc.

# Changing the labels at each beat

    {{% raw %}}
	{{% causal_diagram %}}
	3 3 3 3 3
	(LR) 3 3 3 3 3
	(LLRR) 3 3 3 3 3
	(WOMBLE) 3 3 3 3 3
	{{% /causal_diagram %}}
    {{% /raw %}}

Letters in parenthesis will be repeated along the pattern. These can be different for each juggler.

{{% causal_diagram %}}
3 3 3 3 3
(LR) 3 3 3 3 3
(LLRR) 3 3 3 3 3
(WOMBLE) 3 3 3 3 3
{{% /causal_diagram %}}

# Offsets and titles

    {{% raw %}}
	{{% causal_diagram %}}
	(RL 0) 3 3 3 3 3 3
	(LR 0.5) 3 3 3 3 3 3
	(RL 1) 3 3 3 3 3 3
	title: how to do offsets
	{{% /causal_diagram %}}
    {{% /raw %}}

Offsets can be defined and a title for the whole diagram can be set:

{{% causal_diagram %}}
(RL 0) 3 3 3 3 3 3

(LR 0.5) 3 3 3 3 3 3
(RL 1) 3 3 3 3 3 3
title: how to do offsets
{{% /causal_diagram %}}

# Multi-person passes

	{{% raw %}}
	{{% causal_diagram %}}
	3b 3b 3 3 3b 3b 3 3
	3a 3a 3c 3c 3a 3a 3c 3c
	3 3 3b 3b 3 3 3b 3b
	{{% /causal_diagram %}}
    {{% /raw %}}

When the pattern involves multiple jugglers, you define whom you are passing to by using 'a', 'b', etc. instead of 'p'.

{{% causal_diagram %}}
3b 3b 3 3 3b 3b 3 3
3a 3a 3c 3c 3a 3a 3c 3c
3 3 3b 3b 3 3 3b 3b
{{% /causal_diagram %}}

# Bars

    {{% raw %}}
	{{% causal_diagram %}}
	3p 3 4p 2 3 3 3p
	3p 3 3 3p 2 3 3p
	title: An early double in 3 count
	bars:2.5,5.5
	{{% /causal_diagram %}}
    {{% /raw %}}

You can add bars at certain positions to make reading the pattern easier.

{{% causal_diagram %}}
3p 3 4p 2 3 3 3p
3p 3 3 3p 2 3 3p
title: An early double in 3 count
bars:2.5,5.5
{{% /causal_diagram %}}


# Lines styles

You can change the linestyle by adding certain characters at the end of a value.
Allowed symbols are ",#><^*".

    {{% raw %}}
	{{% causal_diagram %}}
	3p> 3 3 3p^ 4, 2 3p
	3p< 3 3 3p# 3 3 3p*
	{{% /causal_diagram %}}

    {{% /raw %}}

{{% causal_diagram %}}
3p> 3 3 3p^ 4, 2 3p
3p< 3 3 3p# 3 3 3p*
{{% /causal_diagram %}}


# Positions (static)

You can also define positions to get a diagram of where people should stand.

    {{% raw %}}
    {{% causal_diagram %}}
    3p 3 3 3p 3 3
    3p 3 3 3p 3 3
    position A: -100,0,0;
    position B: +100,0,180
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3p 3 3 3p 3 3
3p 3 3 3p 3 3
position A: -100,0,0;
position B: +100,0,180
{{% /causal_diagram %}}

Positions need to be defined for each juggler for a position diagram to show up.

Once positions are defined, all passes will be animated in the diagram.

Positions are relative to a center position in the diagram. You can
either specify 2 numbers as ΔX and ΔY or 3 numbers. In which case the
last number is the orientation of the juggler (0=looking to the right,
180 looking to the left).

# Positions (walking)

You can also define walking patterns.


    {{% raw %}}
    {{% causal_diagram %}}
    3d 3 3 3 3 3
    3c 3 3 3 3 3
    3a 3 3 3 3 3
    3b 3 3 3 3 3
    title: Y (walking, 6 count)
    position A: 0,-100,0,0;      6,-200,+100,0;   12,-300,0,0;     18,-200,-100,0;   24,-100,0,0;
    position B: 0,-300,0,0;      6,-200,-100,0;   12,-100,0,0;     18,-200,+100,0;   24,-300,0,0;
    position C: 0,+200,100,180;  6,+100,0,180;    12,200,-100,180; 18,+300,0,180;    24,200,100,180;
    position D: 0,+200,-100,180; 6,+300,0,180;    12,200,+100,180; 18,+100,0,180;    24,200,-100,180;
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3d 3 3 3 3 3
3c 3 3 3 3 3
3a 3 3 3 3 3
3b 3 3 3 3 3
title: Y (walking, 6 count)
position A: 0,-100,0,0;      6,-200,+100,0;   12,-300,0,0;     18,-200,-100,0;   24,-100,0,0;
position B: 0,-300,0,0;      6,-200,-100,0;   12,-100,0,0;     18,-200,+100,0;   24,-300,0,0;
position C: 0,+200,100,180;  6,+100,0,180;    12,200,-100,180; 18,+300,0,180;    24,200,100,180;
position D: 0,+200,-100,180; 6,+300,0,180;    12,200,+100,180; 18,+100,0,180;    24,200,-100,180;
{{% /causal_diagram %}}

In this case you need to always specify 4 values and specify multiple positions that are separated by ";".

The first number now specifies a time step. The last time step should be the same for every juggler. If the number of time steps is larger than the number of beats in the diagram. The pattern will just repeat. However the largest time step should be a multiple of the number of beats in the pattern.

Note that the number of positions for each juggler can vary.

Currently, the last position should be the same as the first to achieve a smooth pattern.


# Continuation lines

If lines get too long, you can break them up into multiple lines by using the '\' character at the end.


    {{% raw %}}
    {{% causal_diagram %}}
    3d 3 3 3 3 3
    3c 3 3 3 3 3
    3a 3 3 3 3 3
    3b 3 3 3 3 3
    title: Y (walking, 6 count)
    position A: 0,-100,0,0;     \
                6,-200,+100,0;  \
                12,-300,0,0;    \
                18,-200,-100,0; \
                24,-100,0,0;
    position B: 0,-300,0,0;      6,-200,-100,0;   12,-100,0,0;     18,-200,+100,0;   24,-300,0,0;
    position C: 0,+200,100,180;  6,+100,0,180;    12,200,-100,180; 18,+300,0,180;    24,200,100,180;
    position D: 0,+200,-100,180; 6,+300,0,180;    12,200,+100,180; 18,+100,0,180;    24,200,-100,180;
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3d 3 3 3 3 3
3c 3 3 3 3 3
3a 3 3 3 3 3
3b 3 3 3 3 3
title: Y (walking, 6 count)
position A: 0,-100,0,0;     \
            6,-200,+100,0;  \
			12,-300,0,0;    \
			18,-200,-100,0; \
			24,-100,0,0;
position B: 0,-300,0,0;      6,-200,-100,0;   12,-100,0,0;     18,-200,+100,0;   24,-300,0,0;
position C: 0,+200,100,180;  6,+100,0,180;    12,200,-100,180; 18,+300,0,180;    24,200,100,180;
position D: 0,+200,-100,180; 6,+300,0,180;    12,200,+100,180; 18,+100,0,180;    24,200,-100,180;
{{% /causal_diagram %}}
