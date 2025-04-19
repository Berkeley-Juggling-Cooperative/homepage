<!--
.. title: Havana
.. slug: havana
.. date: 2025-03-13 21:35:57 UTC-07:00
.. tags: 4-person, 3-clubs-each, walking
.. category: patterns
.. link:
.. description: Havana
.. type: text
-->

A walking pattern where you always turn left ;) 5 beat pattern with changing feeder.
The person feeding is doing a 2 count, all other three positions a 6 count.

{{% causal_diagram %}}
# Feeder
# A                        B                        C                        D
# passes
# 1    2    3    4    5    1    2    3    4    5    1    2    3    4    5    1    2    3    4    5
# animation beats
# 0  1 2  3 4  5 6  7 8  9 10  12   14   16   18   20   22   24   26   28   30   32   34   36   38 39
  3d 3 3c 3 3b 3 3d 3 3c 3 3b 3 3  3 3  3 3b 3 3  3 3  3 3c 3 3  3 3  3 3c 3 3  3 3  3 3d 3 3  3 3  3
  3  3 3  3 3a 3 3  3 3  3 3a 3 3d 3 3c 3 3a 3 3d 3 3c 3 3  3 3  3 3c 3 3  3 3  3 3d 3 3  3 3  3 3d 3
  3  3 3a 3 3  3 3  3 3a 3 3  3 3  3 3b 3 3  3 3  3 3b 3 3a 3 3d 3 3b 3 3a 3 3d 3 3  3 3  3 3d 3 3  3
  3a 3 3  3 3  3 3a 3 3  3 3  3 3b 3 3  3 3  3 3b 3 3  3 3  3 3c 3 3  3 3  3 3c 3 3b 3 3a 3 3c 3 3b 3
title: Havana
bars: 9.5,19.5,29.5
position A:  0,-100,   0, @B;\  # feeding
	         2,-100,   0, @C;\
	         4,-100,   0, @D;\
	         6,-100,   0, @B;\
	         8,-100,   0, @C;\
	        10,-100,   0, @B;\
		    16, -25, -43, @B;\  # swapping
			22,   0,   0, @C;\  # in Havanna
		    28,  50,  86, @C;\
			39,  50,  86, @D;

position B:  0,  50,  86, @A;\
            10,  50,  86, @A;\
            12,  50,  86, @D;\  # feeding
            14,  50,  86, @C;\
            16,  50,  86, @A;\
            18,  50,  86, @D;\
            20,  50,  86, @C;\
			26, -25,  43, @C;\
			32,   0,   0, @D;\  # in Havanna
			38,  50, -86, @D;\
			39,  50, -86, @D;

position C:  0,  50,   0, @A;\
             2,  24, -43, @A;\
			 8,  50, -86, @A;\
		    20,  50, -86, @B;\  # feeding
		    22,  50, -86, @A;\
		    24,  50, -86, @D;\
		    26,  50, -86, @B;\
		    28,  50, -86, @A;\
		    30,  50, -86, @D;\
			36,  50,   0, @D;\
			39,   0,   0, @D;   # in Havanna

position D:  0,  50, -86, @A;\
             6,  50,   0, @A;\
            12,   0,   0, @B;\  # in Havanna
			18,-100,   0, @B;\
			24,-100,   0, @C;\
			30,-100,   0, @C;\  # feeding
			32,-100,   0, @B;\
			34,-100,   0, @A;\
			36,-100,   0, @C;\
			38,-100,   0, @B;\
			39,-100,   0, @A;
{{% /causal_diagram %}}
