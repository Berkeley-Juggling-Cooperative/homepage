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

Most of this is based on [this article](https://jugglingedge.com/help/causaldiagrams.php).

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

# multi-person passes

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
