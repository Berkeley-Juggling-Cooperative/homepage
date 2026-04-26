<!--
.. title: Rotating Torture Chamber
.. slug: rotating_torture_chamber
.. date: 2025-04-25 19:45:31 UTC-07:00
.. tags: 5-person, 3-clubs-each, 4-count, torture-chamber
.. category: patterns
.. link:
.. description: Rotating Torture chamber
.. type: text
-->

A more complex version of [Torture
Chamber](link:///patterns/torture_chamber) where the outside people
have a bit more to do.

The pattern is otherwise the same as the static version, but here, the
center person rotate 90 degree after one cycle of the pattern.

To make the causal diagram a bit more compact, we show this version in
2 count, although 4 count is probably a better speed for this.

{{% causal_diagram %}}
#A is facing...
#B                   C                   D                   E
# beats
#0  1 2  3 4  5 6  7 8  9 10   12   14   16   18   20   22   24   26   28   30
 3b 3 3c 3 3d 3 3e 3 3c 3 3d 3 3e 3 3b 3 3d 3 3e 3 3b 3 3c 3 3e 3 3b 3 3c 3 3d 3
 3a 3 3e 3 3a 3 3c 3 3e 3 3a 3 3c 3 3a 3 3c 3 3  3 3c 3 3  3 3  3 3e 3 3  3 3e 3
 3  3 3b 3 3  3 3b 3 3a 3 3b 3 3a 3 3d 3 3b 3 3a 3 3d 3 3a 3 3d 3 3  3 3d 3 3  3
 3e 3 3  3 3e 3 3  3 3  3 3c 3 3  3 3c 3 3a 3 3c 3 3a 3 3e 3 3c 3 3a 3 3e 3 3a 3
 3d 3 3a 3 3b 3 3a 3 3b 3 3  3 3b 3 3  3 3  3 3d 3 3  3 3d 3 3a 3 3d 3 3a 3 3b 3

bars: 7.5,15.5,23.5

position A: 0,    0,    0, @B;\
            7,    0,    0, @B;\
            8,    0,    0, @C;\
            15,   0,    0, @C;\
            16,   0,    0, @D;\
            23,   0,    0, @D;\
            24,   0,    0, @E;\
            30,   0,    0, @E;\
            31,   0,    0, @B
position B: 0, -100, -100, @0;\
           31, -100, -100, @0;
position C: 0, -100,  100, @B;\
            7, -100,  100, @B;\
			8, -100,  100, @0;\
		   31, -100,  100, @0;
position D: 0,  100,  100, @E;\
            7,  100,  100, @E;\
			8,  100,  100, @C;\
		   31,  100,  100, @0;
position E: 0,  100, -100, @0;\
            7,  100, -100, @0;\
			8,  100, -100, @B;\
		   31,  100, -100, @0;


{{% /causal_diagram %}}

