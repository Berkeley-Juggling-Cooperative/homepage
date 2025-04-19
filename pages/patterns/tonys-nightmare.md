<!--
.. title: Double rotating token feed (Tony's nightmare)
.. slug: tonys-nightmare
.. date: 2025-04-19 10:29:50 UTC-07:00
.. tags: 5-person, 3-club-each, 4-count, 2-count
.. category: patterns
.. link:
.. description: Tony's nightmare
.. type: text
-->

This has two [Rotating Feeds](link:///patterns/rotating-feed) interlocked.

You start in a circle. One person is feeding everyone.

A beat later, a second person starts the second rotation. This person
should be two to the right of the first feeder (from the first
feeder's point of view).

Whenever you get a pass from the person on your left, you start a
rotating feed.

It helps if each person calls out 'feeder' when they start their feed.

Each person does the following:

* a rotating feed
* a self
* a rotating feed
* two selfs
* a pass to the person two to the left
* a pass to the person two to the right
* two selfs

However, everyone starts at a different point in that cycle.

{{% causal_diagram %}}
3b$ 3c$ 3d$ 3e$ 3   3   3c  3d  3   3   3b  3c  3d  3e  3
3a^ 3   3   3d  3e  3   3   3c  3d  3e  3a  3   3c^ 3d^ 3e^
3   3a  3   3   3d  3e  3a  3b  3   3d< 3e< 3a< 3b< 3   3
3   3e  3a  3b  3c  3   3e> 3a> 3b> 3c> 3   3   3a  3b  3
3   3d  3   3a@ 3b@ 3c@ 3d@ 3   3   3b  3c  3   3   3a  3b
positions: circle
{{% /causal_diagram %}}
