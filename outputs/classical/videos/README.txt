Actual native MetaUrban 3D closed-loop RGB, not a 2D navigation schematic.

classical_crossing_comparison.mp4
  Development seed902, one prescribed native pedestrian crossing; RPP-inspired / route-velocity forecast / DWA-style, synchronized by simulation time. The robot uses current numerical states, not camera images. Held frames are explicitly labelled after each episode ends. All three examples reach the strict goal without contact. This selected development case explains behavior; see all fresh test rows for aggregate outcomes.

inspection_mission.mp4 and inspection_view.png
  Development seed902,15 native pedestrians. Forecast controller reaches within2m with the native flag, then holds physical speed<0.1m/s for one second and saves an actual street view. No navigation or inspection contact. The maximum speed during the final one-second hold is0.06504m/s.

stationary_limitation.mp4
  Development seed902, one prescribed stationary native pedestrian on the route. The speed-only controller cannot finish within60s; retained to show a blocked-route limit, not presented as a success.

Rendering repeats match their physics-only counterparts exactly for ego positions, executed actions and pedestrian positions. Central video_acceptance.json records the checks; its contact_free field means CONTACT-FREE STRICT ARRIVAL, not merely absence of contact on an unfinished path.

Single video/image entries use hard links to the corresponding preserved runs/classical_videos_20261102 files. No cleanup/deletion occurred.
