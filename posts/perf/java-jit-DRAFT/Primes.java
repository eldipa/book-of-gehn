import java.nio.ByteBuffer;
import java.io.File;
import java.io.FileInputStream;
import java.nio.ByteOrder;
import java.io.IOException;

public class Primes {
    private static final String DATA_FILENAME = "numbers.dat";

    private static final int NUMBERS = 1573888;
    private static final int MAX = 1023;

    public static void main(String[] args) {
        int[] numbers = new int[NUMBERS];
        byte [] tmp = new byte[NUMBERS * 4];
        int prime_count = 0;

        if (args.length != 1) {
            System.exit(1);
        }

        int rounds = 0;
        try {
            rounds = Integer.parseInt(args[0]);
            if (rounds <= 0) {
               System.exit(1);
            }
        } catch (NumberFormatException e) {
            System.exit(1);
        }

        try {
            FileInputStream f = new FileInputStream(new File(DATA_FILENAME));
            f.read(tmp);
            f.close();
        } catch (IOException e) {
            e.printStackTrace();
        }

        ByteBuffer tmpbuf = ByteBuffer.wrap(tmp);
        tmpbuf.order(ByteOrder.LITTLE_ENDIAN);

        for (int i = 0; i < NUMBERS; i++) {
            numbers[i] = tmpbuf.getInt(i*4);
        }

        tmpbuf = null;

        long begin = System.nanoTime();
        mainloop:
        while (rounds > 0) {
            for (int div = 2; div < MAX; ++div) {
                for (int i = 0; i < NUMBERS; ++i) {
                    if (div < numbers[i]) {
                        if (numbers[i] % div == 0) {
                            prime_count++;
                        }
                    }

                    rounds--;

                    if (rounds <= 0) {
                        break mainloop;
                    }
                }
            }
        }

        long elapsed = System.nanoTime() - begin;

        System.out.println("Found "+prime_count+" primes.");
        System.out.println("Took "+elapsed/1000+" microseconds.");
    }

}

