# The bumps. Executed by build.py (which provides bump(), cards(), footage(), frames(), black()...).
# Copy rules: lowercase, dry, first person plural, no "up next".

OVER = dict(shadow=1.0, size=44, y=0.74)          # type sitting on footage
BOXED = dict(size=33, y=0.865, maxw=0.8)          # type under a 4:3 window
BIG = dict(size=54, y=0.5, maxw=0.82)             # type alone on black
WINDOW = (640, 480, 320, 50)                      # a 4:3 window, top centre

# ── type on black ───────────────────────────────────────
bump(id='ratings', title='the overnights', desc='the ratings are in. it is you.',
     bg=black,
     cards=cards(['the overnight ratings are in.', 'one viewer.', 'that is up 100% since you got here.', 'no pressure.'], **BIG))

bump(id='twelve', title='twelve seconds', desc='a break that keeps its own time.',
     bg=black,
     cards=cards(['this break is twelve seconds long.', 'you have now used four of them.', 'eight.', 'ten. it goes fast.'],
                 [(0.25, 3.85), (4.0, 7.85), (8.0, 9.85), (10.0, 11.5)], **BIG))

bump(id='clock', title='no control room', desc='how the station works, in four cards.',
     bg=black,
     cards=cards(['there is no control room.', 'there is a clock and a list of films.',
                  'everyone watching right now is on the same frame as you.',
                  'we think that is two or three people. hello.'], **BIG))

bump(id='mail', title='a complaint', desc='viewer mail, answered in full.',
     bg=black,
     cards=cards(['we received a complaint.', ('“there is no way to choose what to watch.”', dict(face='regular')),
                  'correct.', 'thank you for writing in.'], **BIG))

# ── very old film, in a window ──────────────────────────
bump(id='sneeze', title='fred ott', desc='the oldest copyrighted film in america is a sneeze.',
     bg=lambda bid: footage(bid, 'sneeze', 13.0, loop=4, box=WINDOW, grade=dim(0.86)),
     cards=cards(['january 1894. a man named fred sneezes for a camera.',
                  'it is the oldest surviving copyrighted film in america.',
                  'we have been making television out of less ever since.'], **BOXED),
     poster=5.0)


def horse_bg(bid):
    out = os.path.join(wdir(bid), 'bg.mp4')
    # 11 distinct photographs in the source, each held for several frames: keep one of each,
    # show each for two frames (12 fps), loop the stride for the whole bump
    ffmpeg('-i', src('horse'), '-vf',
           SQUARE + ",mpdecimate=hi=64*40:lo=64*12:frac=0.2,setpts=N/12/TB,fps=%d,"
           "scale=780:520:force_original_aspect_ratio=increase,crop=780:520,%s,"
           "loop=loop=-1:size=22:start=0,trim=end_frame=%d,pad=%d:%d:250:40:black" % (FPS, dim(0.84), FRAMES, W, H),
           '-frames:v', FRAMES, *ENC_MID, out)
    return out


bump(id='horse', title='sallie gardner', desc='1878. the first rerun.',
     bg=horse_bg,
     cards=cards(['1878. a man photographs a horse to find out if all four hooves ever leave the ground.',
                  'they do.', 'this was the first rerun.'], **dict(BOXED, y=0.88)),
     poster=5.0)

# ── held shots ──────────────────────────────────────────
bump(id='jelly', title='3,700 meters', desc='a jellyfish near the mariana trench, with no audience.',
     bg=lambda bid: footage(bid, 'jelly', 9.3, speed=0.62, grade='eq=contrast=1.06:saturation=1.1'),
     cards=cards(['3,700 meters under the pacific.',
                  'this jellyfish has been broadcasting to no one its whole life.',
                  'we know the feeling.'], **dict(OVER, x=0.53, y=0.2, align='left', maxw=0.43, size=38)))

bump(id='snow', title='it is always snowing', desc='a streetlight in sweden, and the premise of the channel.',
     bg=lambda bid: footage(bid, 'snow', 3.0, grade='eq=contrast=1.15:brightness=0.02'),
     cards=cards(['it is always snowing in here.', 'that is how a snow globe works.',
                  'we don’t know who keeps shaking it.'], **dict(OVER, y=0.76)))

# ── built in blender ────────────────────────────────────
bump(id='station', title='the whole station', desc='the transmitter, the house, the weather. on a shelf.',
     bg=frames, weight=1.5,
     cards=cards(['this is the whole station.', 'one person picks the films.\na clock does the rest.',
                  'you cannot change the channel.\nwe checked.'], **dict(OVER, y=0.84, size=40)))

bump(id='market', title='market street', desc='san francisco, 1906, from the front of a cable car.',
     bg=lambda bid: footage(bid, 'market', 204, grade='hqdn3d=3:3:6:6,' + dim(0.62, 1.08) + ',' + VIGNETTE),
     cards=cards(['san francisco, 1906. someone bolted a camera to the front of a cable car.',
                  'none of these people know they are on television.',
                  'we don’t know how to tell them.'], **dict(OVER, y=0.76, maxw=0.7)))

bump(id='orbit', title='still up', desc='the night side of the earth from the space station.',
     bg=lambda bid: footage(bid, 'orbit', 27, grade='eq=contrast=1.08'),
     cards=cards(['this is the night side of the earth, from the space station.',
                  'every light down there is somebody who is still up.',
                  'so it isn’t just you.'], **dict(OVER, y=0.8, maxw=0.7)),
     blocks=['evening', 'latenight', 'deadhours'])

bump(id='lava', title='lava lake', desc='the crust of a lava lake at kīlauea, breaking up and coming back.',
     bg=lambda bid: footage(bid, 'lava2', 13, pre='crop=iw*0.86:ih*0.86:iw*0.14:ih*0.14', grade='hqdn3d=4:4:8:8,eq=contrast=1.1:saturation=1.15'),
     cards=cards(['this is a lake of lava at the top of kīlauea.',
                  'the crust breaks up, sinks and grows back. it did that for ten years.',
                  'we would have watched most of it.'], **dict(OVER, y=0.85, maxw=0.74, size=40)))


def hands_bg(bid):
    pre = 'crop=1440:1080:240:0'
    g = 'hqdn3d=3:3:7:7,eq=contrast=1.1:brightness=0.02'
    return concat(bid, [footage(bid, 'hands', t, length=4, pre=pre, grade=g, name='p%d' % i)
                        for i, t in enumerate((169.5, 309.5, 351.0))])


bump(id='hands', title='master hands', desc='a 1936 factory film with a full orchestra.',
     bg=hands_bg,
     cards=cards(['flint, michigan. 1936.', 'chevrolet hired an orchestra to score its assembly line.',
                  'we think about that a lot.'], **dict(OVER, y=0.78)),
     blocks=['morning', 'afternoon', 'evening'])


def remote_bg(bid):
    g = 'eq=contrast=1.06:saturation=1.08'
    return concat(bid, [footage(bid, 'remote', t, length=4, grade=g, name='p%d' % i)
                        for i, t in enumerate((57.0, 180.5, 259.5))])


bump(id='remote', title='the remote', desc='a 1961 demonstration of a thing this channel does not have.',
     bg=remote_bg,
     cards=cards(['1961. you no longer have to get up to change the channel.',
                  'sixty-five years of progress followed.',
                  'here you can’t change it at all.\nyou’re welcome.'], **dict(OVER, y=0.81, maxw=0.7)))

bump(id='bert', title='bert', desc='the turtle the government made in 1951.',
     bg=lambda bid: footage(bid, 'bert', 8.3, box=WINDOW, grade=dim(0.9)),
     cards=cards(['this is bert. the government made him in 1951.',
                  'his job was to get children ready for the atomic bomb.',
                  'he is a turtle. he did what he could.'], **BOXED),
     poster=2.0)

bump(id='tvfield', title='left on', desc='a television in a field, overnight, in the snow.',
     bg=frames,
     cards=cards(['we left a television outside overnight.', 'it kept going.',
                  'nobody was watching.\nthat has never stopped us.'], **dict(OVER, y=0.84, size=40)))

bump(id='train', title='the other train', desc='a smaller train than the one from bergen to oslo.',
     bg=frames,
     cards=cards(['some nights we air a seven-hour train ride from bergen to oslo.',
                  'this train is smaller and goes in a circle.',
                  'one lap takes six seconds. same idea.'], **dict(OVER, y=0.14, size=38, maxw=0.72)))

bump(id='pingpong', title='anything we wanted', desc='four hundred ping pong balls, as requested.',
     bg=lambda bid: frames(bid, vf=dim(0.82)),
     cards=cards(['for this one we were told we could have anything we wanted.',
                  'we asked for four hundred ping pong balls.',
                  'nobody asked a follow-up question.'], **dict(OVER, y=0.17, size=38, maxw=0.72, shadow=1.3)),
     poster=6.0)

bump(id='sponsor', title='a word from our sponsor', desc='there isn’t one. the pedestal is nice.',
     bg=frames,
     cards=cards(['and now, a word from our sponsor.', 'there isn’t one.', 'the pedestal is nice, though.'],
                 **dict(OVER, y=0.13, size=40)),
     poster=4.4)
