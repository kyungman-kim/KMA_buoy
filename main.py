import matplotlib.pyplot as plt
from datetime import datetime

# 테스트용 가짜 데이터
hours = list(range(24))
temps = [10 + i*0.5 for i in hours]

plt.plot(hours, temps)
plt.title(f"Test plot {datetime.now()}")
plt.savefig("plot.png")
print("Done")
