from gym.envs.registration import register

register(
    id='myenv-v0',
    entry_point='myenv.my_breakout:Environment'
)